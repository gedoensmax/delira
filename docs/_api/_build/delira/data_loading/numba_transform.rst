.. role:: hidden
    :class: hidden-section

Numba Wrapper
-------------

Wrapping our transforms with ``numba`` allows us to compile them just-in-time (jit),
parallelize and vectorize them if possible and also enables us to execute them on GPU.

.. currentmodule:: delira.data_loading.numba_transform

:hidden:`NumbaTransformWrapper`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: NumbaTransformWrapper
    :members:
    :undoc-members:
    :show-inheritance:

:hidden:`NumbaTransform`
~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: NumbaTransform
    :members:
    :undoc-members:
    :show-inheritance:

:hidden:`NumbaCompose`
~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: NumbaCompose
    :members:
    :undoc-members:
    :show-inheritance:
