import numpy as np

from .base import DifferentiableModel


class PyTorchModel(DifferentiableModel):
    """Creates a :class:`Model` instance from a `PyTorch` module.

    Parameters
    ----------
    model : `torch.nn.Module`
        The PyTorch model that should be attacked.
    bounds : tuple
        Tuple of lower and upper bound for the pixel values, usually
        (0, 1) or (0, 255).
    num_classes : int
        Number of classes for which the model will output predictions.
    channel_axis : int
        The index of the axis that represents color channels.
    cuda : bool
        A boolean specifying whether the model uses CUDA.
    preprocess_fn : function
        Will be called with the images before model predictions are calculated.

    """

    def __init__(
            self,
            model,
            bounds,
            num_classes,
            channel_axis=1,
            cuda=True,
            preprocess_fn=None):

        super(PyTorchModel, self).__init__(bounds=bounds,
                                           channel_axis=channel_axis)

        self._num_classes = num_classes
        self._model = model
        self.cuda = cuda

        if preprocess_fn is not None:
            self.preprocessing_fn = lambda x: preprocess_fn(x.copy())
        else:
            self.preprocessing_fn = lambda x: x

    def batch_predictions(self, images):
        # lazy import
        import torch
        from torch.autograd import Variable

        n = len(images)
        images = torch.from_numpy(self.preprocessing_fn(images))
        if self.cuda:  # pragma: no cover
            images = images.cuda()
        images = Variable(images, volatile=True)
        predictions = self._model(images)
        predictions = predictions.data
        if self.cuda:  # pragma: no cover
            predictions = predictions.cpu()
        predictions = predictions.numpy()
        assert predictions.ndim == 2
        assert predictions.shape == (n, self.num_classes())
        return predictions

    def num_classes(self):
        return self._num_classes

    def predictions_and_gradient(self, image, label):
        # lazy import
        import torch
        import torch.nn as nn
        from torch.autograd import Variable

        target = np.array([label])
        target = torch.from_numpy(target)
        if self.cuda:  # pragma: no cover
            target = target.cuda()
        target = Variable(target)

        assert image.ndim == 3
        images = image[np.newaxis]
        images = torch.from_numpy(self.preprocessing_fn(images))
        if self.cuda:  # pragma: no cover
            images = images.cuda()
        images = Variable(images, requires_grad=True)
        predictions = self._model(images)
        ce = nn.CrossEntropyLoss()
        loss = ce(predictions, target)
        loss.backward()
        grad = images.grad

        predictions = predictions.data
        if self.cuda:  # pragma: no cover
            predictions = predictions.cpu()

        predictions = predictions.numpy()
        predictions = np.squeeze(predictions, axis=0)
        assert predictions.ndim == 1
        assert predictions.shape == (self.num_classes(),)

        grad = grad.data
        if self.cuda:  # pragma: no cover
            grad = grad.cpu()
        grad = grad.numpy()
        grad = np.squeeze(grad, axis=0)
        assert grad.shape == image.shape

        return predictions, grad
