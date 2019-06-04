
from delira import get_backends
import unittest

import numpy as np
from functools import partial
from delira.training import Parameters

from delira.data_loading import AbstractDataset


class DummyDataset(AbstractDataset):
    def __init__(self, length):
        super().__init__(None, None)
        self.length = length

    def __getitem__(self, index):
        return {"data": np.random.rand(32),
                "label": np.random.randint(0, 1, 1)}

    def __len__(self):
        return self.length

    def get_sample_from_index(self, index):
        return self.__getitem__(index)


if "CHAINER" in get_backends():
    from delira.models import AbstractChainerNetwork
    import chainer

    # define this outside, because it has to be pickleable, which it won't be, wehn defined inside a function
    class DummyNetworkChainer(AbstractChainerNetwork):
        def __init__(self):
            super().__init__()

            with self.init_scope():
                self.dense_1 = chainer.links.Linear(32, 64)
                self.dense_2 = chainer.links.Linear(64, 1)

        def forward(self, x):
            return {
                "pred":
                    self.dense_2(chainer.functions.relu(
                        self.dense_1(x)))
            }

        @staticmethod
        def closure(model, data_dict: dict, optimizers: dict, losses={},
                    metrics={}, fold=0, **kwargs):
            assert (optimizers and losses) or not optimizers, \
                "Criterion dict cannot be emtpy, if optimizers are passed"

            loss_vals = {}
            metric_vals = {}
            total_loss = 0

            inputs = data_dict.pop("data")
            preds = model(inputs)

            if data_dict:

                for key, crit_fn in losses.items():
                    _loss_val = crit_fn(preds["pred"], *data_dict.values())
                    loss_vals[key] = _loss_val.item()
                    total_loss += _loss_val

                with chainer.using_config("train", False):
                    for key, metric_fn in metrics.items():
                        metric_vals[key] = metric_fn(
                            preds["pred"], *data_dict.values()).item()

            if optimizers:
                model.cleargrads()
                total_loss.backward()
                optimizers['default'].update()

            else:

                # add prefix "val" in validation mode
                eval_loss_vals, eval_metrics_vals = {}, {}
                for key in loss_vals.keys():
                    eval_loss_vals["val_" + str(key)] = loss_vals[key]

                for key in metric_vals:
                    eval_metrics_vals["val_" + str(key)] = metric_vals[key]

                loss_vals = eval_loss_vals
                metric_vals = eval_metrics_vals

            return metric_vals, loss_vals, {k: v.unchain()
                                            for k, v in preds.items()}


class ExperimentTest(unittest.TestCase):

    def setUp(self) -> None:
        test_cases_torch, test_cases_tf, test_cases_chainer = [], [], []
        from sklearn.metrics import mean_absolute_error

        # setup torch testcases
        if "TORCH" in get_backends():
            import torch
            from delira.models.classification import \
                ClassificationNetworkBasePyTorch
            from delira.training.callbacks import \
                ReduceLROnPlateauCallbackPyTorch

            class DummyNetworkTorch(ClassificationNetworkBasePyTorch):

                def __init__(self):
                    super().__init__(32, 1)

                def forward(self, x):
                    return {"pred": self.module(x)}

                @staticmethod
                def _build_model(in_channels, n_outputs):
                    return torch.nn.Sequential(
                        torch.nn.Linear(in_channels, 64),
                        torch.nn.ReLU(),
                        torch.nn.Linear(64, n_outputs)
                    )

                @staticmethod
                def prepare_batch(batch_dict, input_device, output_device):
                    return {"data": torch.from_numpy(batch_dict["data"]
                                                     ).to(input_device,
                                                          torch.float),
                            "label": torch.from_numpy(batch_dict["label"]
                                                      ).to(output_device,
                                                           torch.float)}

            test_cases_torch.append((
                Parameters(fixed_params={
                    "model": {},
                    "training": {
                        "losses": {"CE":
                                   torch.nn.BCEWithLogitsLoss()},
                        "optimizer_cls": torch.optim.Adam,
                        "optimizer_params": {"lr": 1e-3},
                        "num_epochs": 2,
                        "val_metrics": {"mae": mean_absolute_error},
                        "lr_sched_cls": ReduceLROnPlateauCallbackPyTorch,
                        "lr_sched_params": {"mode": "min"}
                    }
                }
                ),
                500,
                50,
                "mae",
                "lowest",
                DummyNetworkTorch))

            self._test_cases_torch = test_cases_torch

        # setup tf tescases
        if "TF" in get_backends():
            from delira.models import ClassificationNetworkBaseTf, \
                AbstractTfNetwork

            import tensorflow as tf

            class DummyNetworkTf(ClassificationNetworkBaseTf):
                def __init__(self):
                    AbstractTfNetwork.__init__(self)
                    self.model = self._build_model(1)

                    images = tf.placeholder(shape=[None, 32],
                                            dtype=tf.float32)
                    labels = tf.placeholder_with_default(
                        tf.zeros([tf.shape(images)[0], 1]), shape=[None, 1])

                    preds_train = self.model(images, training=True)
                    preds_eval = self.model(images, training=False)

                    self.inputs["images"] = images
                    self.inputs["labels"] = labels
                    self.outputs_train["pred"] = preds_train
                    self.outputs_eval["pred"] = preds_eval

                @staticmethod
                def _build_model(n_outputs):
                    return tf.keras.models.Sequential(
                        layers=[
                            tf.keras.layers.Dense(64, input_shape=(
                                32,), bias_initializer='glorot_uniform'),
                            tf.keras.layers.ReLU(),
                            tf.keras.layers.Dense(
                                n_outputs,
                                bias_initializer='glorot_uniform')]
                    )

            test_cases_tf.append(
                (
                    Parameters(fixed_params={
                        "model": {},
                        "training": {
                            "losses": {"CE":
                                       tf.losses.softmax_cross_entropy},
                            "optimizer_cls": tf.train.AdamOptimizer,
                            "optimizer_params": {"learning_rate": 1e-3},
                            "num_epochs": 2,
                            "val_metrics": {"mae": mean_absolute_error},
                            "lr_sched_cls": None,
                            "lr_sched_params": {}}
                    }
                    ),
                    500,
                    50,
                    DummyNetworkTf)
            )

        self._test_cases_tf = test_cases_tf

        if "CHAINER" in get_backends():
            import chainer

            test_cases_chainer.append(
                (
                    Parameters(fixed_params={
                        "model": {},
                        "training": {
                            "losses": {
                                "L1":
                                    chainer.functions.mean_absolute_error},
                            "optimizer_cls": chainer.optimizers.Adam,
                            "optimizer_params": {},
                            "num_epochs": 2,
                            "val_metrics": {"mae": mean_absolute_error},
                            "lr_sched_cls": None,
                            "lr_sched_params": {}}
                    }
                    ),
                    500,
                    50,
                    DummyNetworkChainer)
            )

        self._test_cases_chainer = test_cases_chainer

    @unittest.skipIf("TORCH" not in get_backends(),
                     reason="No TORCH Backend installed")
    def test_experiment_run_torch(self):

        from delira.training import PyTorchExperiment
        from delira.data_loading import BaseDataManager

        for case in self._test_cases_torch:
            with self.subTest(case=case):

                (params, dataset_length_train, dataset_length_test,
                 val_score_key, val_score_mode, network_cls) = case

                exp = PyTorchExperiment(params, network_cls,
                                        key_mapping={"x": "data"},
                                        val_score_key=val_score_key,
                                        val_score_mode=val_score_mode)

                dset_train = DummyDataset(dataset_length_train)
                dset_test = DummyDataset(dataset_length_test)

                dmgr_train = BaseDataManager(dset_train, 16, 4, None)
                dmgr_test = BaseDataManager(dset_test, 16, 1, None)

                exp.run(dmgr_train, dmgr_test)

    @unittest.skipIf("TORCH" not in get_backends(),
                     reason="No TORCH Backend installed")
    def test_experiment_test_torch(self):
        from delira.training import PyTorchExperiment
        from delira.data_loading import BaseDataManager

        for case in self._test_cases_torch:
            with self.subTest(case=case):
                (params, dataset_length_train, dataset_length_test,
                 val_score_key, val_score_mode, network_cls) = case

                exp = PyTorchExperiment(params, network_cls,
                                        key_mapping={"x": "data"},
                                        val_score_key=val_score_key,
                                        val_score_mode=val_score_mode)

                model = network_cls()

                dset_test = DummyDataset(dataset_length_test)
                dmgr_test = BaseDataManager(dset_test, 16, 1, None)

                prepare_batch = partial(
                    model.prepare_batch,
                    output_device="cpu",
                    input_device="cpu")

                exp.test(model, dmgr_test,
                         params.nested_get("val_metrics"),
                         prepare_batch=prepare_batch)

    @unittest.skipIf("TORCH" not in get_backends(),
                     reason="No TORCH Backend installed")
    def test_experiment_kfold_torch(self):
        from delira.training import PyTorchExperiment
        from delira.data_loading import BaseDataManager
        from copy import deepcopy

        # all test cases
        for case in self._test_cases_torch:
            with self.subTest(case=case):
                (params, dataset_length_train,
                 dataset_length_test, val_score_key,
                 val_score_mode, network_cls) = case

                # both split_types
                for split_type in ["random", "stratified", "error"]:
                    with self.subTest(split_type=split_type):
                        if split_type == "error":
                            # must raise ValueError
                            with self.assertRaises(ValueError):
                                exp = PyTorchExperiment(
                                    params, network_cls,
                                    key_mapping={"x": "data"},
                                    val_score_key=val_score_key,
                                    val_score_mode=val_score_mode)

                                dset = DummyDataset(
                                    dataset_length_test + dataset_length_train)

                                dmgr = BaseDataManager(dset, 16, 1, None)
                                exp.kfold(
                                    dmgr,
                                    params.nested_get("val_metrics"),
                                    shuffle=True,
                                    split_type=split_type,
                                    num_splits=2)

                            continue

                        # check all types of validation data
                        for val_split in [0.2, None]:
                            with self.subTest(val_split=val_split):

                                # disable lr scheduling if no validation data
                                # is present
                                _params = deepcopy(params)
                                if val_split is None:
                                    _params["fixed"]["training"
                                                     ]["lr_sched_cls"] = None
                                exp = PyTorchExperiment(
                                    _params, network_cls,
                                    key_mapping={"x": "data"},
                                    val_score_key=val_score_key,
                                    val_score_mode=val_score_mode)

                                dset = DummyDataset(
                                    dataset_length_test + dataset_length_train)

                                dmgr = BaseDataManager(dset, 16, 1, None)
                                exp.kfold(
                                    dmgr,
                                    params.nested_get("val_metrics"),
                                    shuffle=True,
                                    split_type=split_type,
                                    val_split=val_split,
                                    num_splits=2)

    @unittest.skipIf("TF" not in get_backends(),
                     reason="No TF Backend installed")
    def test_experiment_run_tf(self):

        from delira.training import TfExperiment
        from delira.data_loading import BaseDataManager

        for case in self._test_cases_tf:
            with self.subTest(case=case):
                (params, dataset_length_train, dataset_length_test,
                 network_cls) = case

                exp = TfExperiment(params, network_cls,
                                   key_mapping={"images": "data"})

                dset_train = DummyDataset(dataset_length_train)
                dset_test = DummyDataset(dataset_length_test)

                dmgr_train = BaseDataManager(dset_train, 16, 4, None)
                dmgr_test = BaseDataManager(dset_test, 16, 1, None)

                exp.run(dmgr_train, dmgr_test)

    @unittest.skipIf("TF" not in get_backends(),
                     reason="No TF Backend installed")
    def test_experiment_test_tf(self):
        from delira.training import TfExperiment
        from delira.data_loading import BaseDataManager

        for case in self._test_cases_tf:
            with self.subTest(case=case):
                (params, dataset_length_train, dataset_length_test,
                 network_cls) = case

                exp = TfExperiment(params, network_cls,
                                   key_mapping={"images": "data"},
                                   )

                model = network_cls()

                dset_test = DummyDataset(dataset_length_test)
                dmgr_test = BaseDataManager(dset_test, 16, 1, None)

                exp.test(model, dmgr_test, params,
                         params.nested_get("val_metrics"))

    @unittest.skipIf("TF" not in get_backends(),
                     reason="No TF Backend installed")
    def test_experiment_kfold_tf(self):
        from delira.training import TfExperiment
        from delira.data_loading import BaseDataManager

        # all test cases
        for case in self._test_cases_tf:
            with self.subTest(case=case):

                # both split_types
                for split_type in ["random", "stratified", "error"]:
                    with self.subTest(split_type=split_type):
                        if split_type == "error":
                            # must raise ValueError
                            with self.assertRaises(ValueError):
                                (params, dataset_length_train,
                                 dataset_length_test, network_cls) = case

                                exp = TfExperiment(
                                    params, network_cls,
                                    key_mapping={"images": "data"})

                                dset = DummyDataset(
                                    dataset_length_test + dataset_length_train)

                                dmgr = BaseDataManager(dset, 16, 1, None)
                                exp.kfold(
                                    dmgr,
                                    params.nested_get("val_metrics"),
                                    shuffle=True,
                                    split_type=split_type,
                                    num_splits=2)

                            continue

                        # check all types of validation data
                        for val_split in [0.2, None]:
                            with self.subTest(val_split=val_split):
                                (params, dataset_length_train,
                                 dataset_length_test, network_cls) = case

                                exp = TfExperiment(
                                    params, network_cls,
                                    key_mapping={"images": "data"})

                                dset = DummyDataset(
                                    dataset_length_test + dataset_length_train)

                                dmgr = BaseDataManager(dset, 16, 1, None)
                                exp.kfold(
                                    dmgr,
                                    params.nested_get("val_metrics"),
                                    shuffle=True,
                                    split_type=split_type,
                                    val_split=val_split,
                                    num_splits=2,
                                )

    @unittest.skipIf("CHAINER" not in get_backends(),
                     reason="No CHAINER Backend installed")
    def test_experiment_run_chainer(self):

        from delira.training import ChainerExperiment
        from delira.data_loading import BaseDataManager

        for case in self._test_cases_chainer:
            with self.subTest(case=case):
                (params, dataset_length_train, dataset_length_test,
                 network_cls) = case

                exp = ChainerExperiment(params, network_cls,
                                        key_mapping={"x": "data"})

                dset_train = DummyDataset(dataset_length_train)
                dset_test = DummyDataset(dataset_length_test)

                dmgr_train = BaseDataManager(dset_train, 16, 4, None)
                dmgr_test = BaseDataManager(dset_test, 16, 1, None)

                exp.run(dmgr_train, dmgr_test)

    @unittest.skipIf("CHAINER" not in get_backends(),
                     reason="No CHAINER Backend installed")
    def test_experiment_test_chainer(self):
        from delira.training import ChainerExperiment
        from delira.data_loading import BaseDataManager

        for case in self._test_cases_chainer:
            with self.subTest(case=case):
                (params, dataset_length_train, dataset_length_test,
                 network_cls) = case

                exp = ChainerExperiment(params, network_cls,
                                        key_mapping={"x": "data"},
                                        )

                model = network_cls()

                dset_test = DummyDataset(dataset_length_test)
                dmgr_test = BaseDataManager(dset_test, 16, 1, None)

                exp.test(model, dmgr_test, params.nested_get("val_metrics"))

    @unittest.skipIf("CHAINER" not in get_backends(),
                     reason="No CHAINER Backend installed")
    def test_experiment_run_chainer(self):

        from delira.training import ChainerExperiment
        from delira.data_loading import BaseDataManager

        for case in self._test_cases_chainer:
            with self.subTest(case=case):
                (params, dataset_length_train, dataset_length_test,
                 network_cls) = case

                exp = ChainerExperiment(params, network_cls,
                                        key_mapping={"x": "data"})

                dset_train = DummyDataset(dataset_length_train)
                dset_test = DummyDataset(dataset_length_test)

                dmgr_train = BaseDataManager(dset_train, 16, 4, None)
                dmgr_test = BaseDataManager(dset_test, 16, 1, None)

                exp.run(dmgr_train, dmgr_test)

    @unittest.skipIf("CHAINER" not in get_backends(),
                     reason="No CHAINER Backend installed")
    def test_experiment_test_chainer(self):
        from delira.training import ChainerExperiment
        from delira.data_loading import BaseDataManager

        for case in self._test_cases_chainer:
            with self.subTest(case=case):
                (params, dataset_length_train, dataset_length_test,
                 network_cls) = case

                exp = ChainerExperiment(params, network_cls,
                                        key_mapping={"x": "data"},
                                        )

                model = network_cls()

                dset_test = DummyDataset(dataset_length_test)
                dmgr_test = BaseDataManager(dset_test, 16, 1, None)

                exp.test(model, dmgr_test, params.nested_get("val_metrics"))


if __name__ == '__main__':
    unittest.main()
