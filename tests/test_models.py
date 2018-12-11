from delira.models import AbstractPyTorchNetwork, UNet2dPyTorch, \
    UNet3dPyTorch, ClassificationNetworkBasePyTorch, \
    VGG3DClassificationNetworkPyTorch, GenerativeAdversarialNetworkBasePyTorch
from delira.training.train_utils import create_optims_default_pytorch, \
    create_optims_gan_default_pytorch
import torch
import numpy as np
import pytest
import time


@pytest.mark.parametrize("model,input_shape,target_shape,loss_fn,"
                         "create_optim_fn,max_range",
                         [
                             # UNet 2D
                             (
                                     UNet2dPyTorch(5, in_channels=1),  # model
                                     (1, 32, 32),  # input shape
                                     (32, 32),  # output shape
                                     {"loss_fn": torch.nn.CrossEntropyLoss()
                                      },  # loss function
                                     create_optims_default_pytorch,  # optim_fn
                                     4  # output range (num_classes -1)
                             ),
                             # UNet 3D
                             (
                                     UNet3dPyTorch(5, in_channels=1),  # model
                                     (1, 32, 32, 32),  # input shape
                                     (32, 32, 32),  # output shape
                                     {"loss_fn": torch.nn.CrossEntropyLoss()
                                      },  # loss function
                                     create_optims_default_pytorch,  # optim_fn
                                     4  # output range (num_classes) - 1
                             ),
                             # Base Classifier (Resnet 18)
                             (
                                     ClassificationNetworkBasePyTorch(1, 10),
                                     # model
                                     (1, 224, 224),  # input shape
                                     9,  # output shape (num_classes - 1)
                                     {"loss_fn": torch.nn.CrossEntropyLoss()
                                      },  # loss function
                                     create_optims_default_pytorch,  # optim_fn
                                     None  # no max_range needed
                             ),
                             # 3D VGG
                             (
                                     VGG3DClassificationNetworkPyTorch(1, 10),
                                     # model
                                     (1, 32, 224, 224),  # input shape
                                     9,  # output shape (num_classes - 1)
                                     {"loss_fn": torch.nn.CrossEntropyLoss()
                                      },  # loss function
                                     create_optims_default_pytorch,  # optim fn
                                     None  # no max_range needed
                             ),
                             # DCGAN
                             (
                                     GenerativeAdversarialNetworkBasePyTorch(
                                         1, 100),
                                     # model
                                     (1, 64, 64),  # input shape
                                     (1, 1),  # arbitrary shape (not needed)
                                     {"loss_fn": torch.nn.MSELoss()},  # loss
                                     create_optims_gan_default_pytorch,
                                     # optimizer function
                                     1  # standard max range
                             )
                         ])
def test_pytorch_model_default(model: AbstractPyTorchNetwork, input_shape,
                               target_shape, loss_fn, create_optim_fn,
                               max_range):

    start_time = time.time()

    # test backward if optimizer fn is not None
    if create_optim_fn is not None:
        optim = create_optim_fn(model, torch.optim.Adam)

    else:
        optim = {}

    closure = model.closure
    device = torch.device("cpu")
    model = model.to(device)
    prepare_batch = model.prepare_batch

    # classification label: target_shape specifies max label
    if isinstance(target_shape, int):
        label = np.asarray([np.random.randint(target_shape) for i in range(
            10)])
    else:
        label = np.random.rand(10, *target_shape) * max_range

    data_dict = {
        "data": np.random.rand(10, *input_shape),
        "label": label
    }

    try:
        data_dict = prepare_batch(data_dict, device, device)
        closure(model, data_dict, optim, loss_fn, {})
    except Exception as e:
        assert False, "Test for %s not passed: Error: %s" \
                      % (model.__class__.__name__, e)

    end_time = time.time()

    print("Time needed for %s: %.3f" % (model.__class__.__name__, end_time -
                                        start_time))


if __name__ == '__main__':
    # checks if networks are valid (not if they learn something)
    test_pytorch_model_default()
