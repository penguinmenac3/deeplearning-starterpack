# MIT License
# 
# Copyright (c) 2018-2019 Michael Fuerst
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import os
import time
import datetime
import json
import sys
from setproctitle import setproctitle

import tensorflow as tf
from hyperparams.hyperparams import import_params, load_params

import starttf
from starttf.train.params import check_completness
from starttf.utils.session_config import get_default_config
from starttf.data.autorecords import create_input_fn, PHASE_TRAIN, PHASE_VALIDATION
from starttf.utils.plot_losses import create_keras_callbacks
from starttf.utils.create_optimizer import create_keras_optimizer
load_model = tf.keras.models.load_model


PHASE_TRAIN = "train"
PHASE_VALIDATION = "validation"


def rename_fn(fn, name):
    def tmp(*args, **kwargs):
        fn(*args, **kwargs)
    tmp.__name__ = name
    return tmp


def easy_train_and_evaluate(hyper_params, model=None, loss=None,
                            training_data=None, validation_data=None,
                            continue_training=False,
                            session_config=None,
                            continue_with_specific_checkpointpath=None,
                            no_artifacts=False):
    """
    Train and evaluate your model without any boilerplate code.

    1) Write your data using the starttf.tfrecords.autorecords.write_data method.
    2) Create your hyper parameter file containing all required fields and then load it using
        starttf.utils.hyper_params.load_params method.
        Minimal Sample Hyperparams File:
        {"train": {
            "learning_rate": {
                "type": "const",
                "start_value": 0.001
            },
            "optimizer": {
                "type": "adam"
            },
            "batch_size": 1024,
            "iters": 10000,
            "summary_iters": 100,
            "checkpoint_path": "checkpoints/mnist",
            "tf_records_path": "data/.records/mnist"
            }
        }
    3) Pass everything required to this method and that's it.
    :param hyper_params: The hyper parameters obejct loaded via starttf.utils.hyper_params.load_params
    :param Model: A keras model.
    :param create_loss: A create_loss function like that in starttf.examples.mnist.loss.
    :param inline_plotting: When you are using jupyter notebooks you can tell it to plot the loss directly inside the notebook.
    :param continue_training: Bool, continue last training in the checkpoint path specified in the hyper parameters.
    :param session_config: A configuration for the session.
    :return:
    """
    check_completness(hyper_params)
    starttf.hyperparams = hyper_params
    time_stamp = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H.%M.%S')
    chkpt_path = hyper_params.train.checkpoint_path + "/" + time_stamp
    chkpt_path = chkpt_path + "_" + hyper_params.train.experiment_name

    if session_config is None:
        session_config = get_default_config()

    tf.keras.backend.set_session(tf.Session(config=session_config))

    if continue_with_specific_checkpointpath:
        chkpt_path = hyper_params.train.checkpoint_path + "/" + continue_with_specific_checkpointpath
        print("Continue with checkpoint: {}".format(chkpt_path))
    elif continue_training:
        chkpts = sorted([name for name in os.listdir(hyper_params.train.checkpoint_path)])
        chkpt_path = hyper_params.train.checkpoint_path + "/" + chkpts[-1]
        print("Latest found checkpoint: {}".format(chkpt_path))

    if not os.path.exists(chkpt_path) and not no_artifacts:
        os.makedirs(chkpt_path)
        
    # If hyperparam config is used
    if model is None:
        p = ".".join(hyper_params.arch.model.split(".")[:-1])
        n = hyper_params.arch.model.split(".")[-1]
        arch_model = __import__(p, fromlist=[n])
        model = arch_model.__dict__[n]()
    if loss is None and hyper_params.arch.get("loss", None) is not None:
        p = ".".join(hyper_params.arch.loss.split(".")[:-1])
        n = hyper_params.arch.loss.split(".")[-1]
        arch_loss = __import__(p, fromlist=[n])
        loss = arch_loss.__dict__[n]()
    if training_data is None and hyper_params.arch.get("prepare", None) is not None:
        p = ".".join(hyper_params.arch.prepare.split(".")[:-1])
        n = hyper_params.arch.prepare.split(".")[-1]
        prepare = __import__(p, fromlist=[n])
        prepare = prepare.__dict__[n]
        training_data = prepare(hyper_params, PHASE_TRAIN)
        validation_data = prepare(hyper_params, PHASE_VALIDATION)
        
    # TODO save code

    # Write hyper parameters to be able to track what config you had.
    if not no_artifacts:
        with open(chkpt_path + "/hyperparameters.json", "w") as json_file:
            json_file.write(json.dumps(hyper_params.to_dict(), indent=4, sort_keys=True))

    if training_data is not None:
        hyper_params.train.steps = hyper_params.train.epochs * len(training_data)
    hyper_params.immutable = True

    losses = {}
    metrics = {}
    if loss is None:
        losses = hyper_params.train.loss.to_dict()
        metrics = hyper_params.train.metrics.to_dict()
    else:
        losses, metrics = loss.losses, loss.metrics
    callbacks = create_keras_callbacks(hyper_params, chkpt_path, no_artifacts=no_artifacts)
    optimizer, lr_sheduler = create_keras_optimizer(hyper_params)
    callbacks.append(lr_sheduler)

    if training_data is None:
        train_features, train_labels = create_input_fn(os.path.join(hyper_params.train.tf_records_path, PHASE_TRAIN),
                                                       hyper_params.train.batch_size)().make_one_shot_iterator().get_next()
        validation_data = create_input_fn(os.path.join(hyper_params.train.tf_records_path, PHASE_VALIDATION),
                                                                 hyper_params.train.batch_size)().make_one_shot_iterator().get_next()

        input_tensor = {k: tf.keras.layers.Input(shape=train_features[k].get_shape().as_list(), name=k) for k in train_features}
        target_placeholders = {k: tf.placeholder(shape=(None,) + train_labels[k].shape[1:], dtype=train_labels[k].dtype, name=k + "_placeholder") for k in train_labels}
        model = model.create_keras_model(**input_tensor)
        # model.metrics_names = [k for k in metrics]
        model.compile(loss=losses, optimizer=optimizer, metrics=metrics, target_tensors=target_placeholders)
        tf.keras.backend.get_session().run(tf.global_variables_initializer())
        model.fit(train_features, train_labels, validation_data=validation_data,
                  batch_size=hyper_params.train.batch_size,
                  steps_per_epoch=hyper_params.train.get("steps_per_epoch", 1),
                  epochs=hyper_params.train.get("epochs", 50),
                  validation_steps=hyper_params.train.get("validation_steps", 1),
                  callbacks=callbacks, verbose=1)
    else:
        # first batches features
        #features = training_data[0][0]
        #model._set_inputs({k: tf.zeros(features[k].shape) for k in features})
        train_features = training_data[0][0]
        train_labels = training_data[0][1]
        input_tensor = {k: tf.keras.layers.Input(shape=train_features[k].shape[1:], name=k) for k in train_features}
        target_placeholders = {k: tf.placeholder(shape=(None,) + train_labels[k].shape[1:], dtype=train_labels[k].dtype, name=k + "_placeholder") for k in train_labels}
        model = model.create_keras_model(**input_tensor)
        # model.metrics_names = [k for k in metrics]
        model.compile(loss=losses, optimizer=optimizer, metrics=metrics, target_tensors=target_placeholders)
        tf.keras.backend.get_session().run(tf.global_variables_initializer())
        model.fit_generator(training_data, validation_data=validation_data, epochs=hyper_params.train.get("epochs", 50),
                            callbacks=callbacks, workers=2, use_multiprocessing=False, shuffle=True, verbose=1)

    return chkpt_path


def main(args):
    if len(args) == 2 or len(args) == 3:
        continue_training = False
        no_artifacts = False
        idx = 1
        if args[idx] == "--continue":
            continue_training = True
            idx += 1
        if args[idx] == "--no_artifacts":
            no_artifacts = True
            idx += 1
        if args[1].endswith(".json"):
            hyperparams = load_params(args[idx])
        elif args[1].endswith(".py"):
            hyperparams = import_params(args[idx])
        setproctitle("train {}".format(hyperparams.train.experiment_name))
        return easy_train_and_evaluate(hyperparams, continue_training=continue_training, no_artifacts=no_artifacts)
    else:
        print("Usage: python -m starttf.estimators.keras_trainer [--continue] hyperparameters/myparams.py")
        return None


if __name__ == "__main__":
    main(sys.argv)