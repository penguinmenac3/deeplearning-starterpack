# MIT License
#
# Copyright (c) 2019 Michael Fuerst
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


PHASE_TRAIN = "train"
PHASE_VALIDATION = "val"
PHASE_TRAINVAL = "trainval"
PHASE_TEST = "test"

NO_PARAMS = object()
hyperparams = None

from starttf.annotations import RunOnce

from starttf.data.simple_sequence import Sequence
from starttf.data.prepare import buffer_dataset_as_tfrecords, create_input_fn, write_data

from starttf.modules.module import Model, Layer
from starttf.modules.loss import Loss
from starttf.modules.metric import Metrics

from starttf.train.params import HyperParams
from starttf.train.keras import easy_train_and_evaluate as train_keras
from starttf.train.supervised import easy_train_and_evaluate as train
# TODO enable line once implemented
#from starttf.train.estimators import easy_train_and_evaluate as train_estimator
