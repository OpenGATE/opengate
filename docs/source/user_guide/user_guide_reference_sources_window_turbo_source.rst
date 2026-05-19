.. _source-window-turbo-source:

Window Turbo Source
=====================

Description
-----------

Window Turbo Source 的作用是让源只对一个矩形窗口发射光子，从而达到节约仿真时间的目的。
在不同场景中，加速比可以达到几十至几百倍，取决于窗口的大小和到源的距离。
这种源是主要为了多针孔准直器SPECT的仿真而设计的，但在其他场景中也能发挥作用。

本源的位置采样、事件时间间隔都经过了特别的处理，使得结果计数的空间与时间统计特性都与使用 GenericSource 进行iso发射相同。具体对比见测试100。
对于每个源来说，都只能定义一个窗口，窗口必须位于平行于z轴的参考平面上，并且窗口的四个边分别与z轴以及xoy平面平行。

.. image:: ../figures/window_turbo_source.png

Window Turbo Source 的所有额外属性都位于direction属性中，如下表所示：


.. list-table::
    :header-rows: 1

    * - **参数**
      - **描述**
    * - ``a1``
      - 窗口左边界，相对于参考平面的中心点
    * - ``a2``
      - 窗口右边界，相对于参考平面的中心点
    * - ``b1``
      - 窗口下边界，相对于参考平面的中心点
    * - ``b2``
      - 窗口上边界，相对于参考平面的中心点
    * - ``plane_distance``
      - 窗口平面距离系统中心的距离
    * - ``plane_phi``
      - 窗口法向量与x轴正向的夹角
    * - ``init_sampling_count``
      - 初始化阶段的采样数量，默认为100万
    * - ``init_number_of_threads``
      - 初始化阶段的线程数量，默认与仿真线程数量相同
    * - ``act_ratio``
      - 活度比例，由初始化得到。默认为nan。
    * - ``max_solid_angle``
      - 最大立体角，由初始化得到。默认为nan。
    * - ``skip_mode``
      - 是否采用跳过模式。采用跳过模式，则事件间隔依靠前一个事件的立体角来修正；否则则会计算一个总体的活度比例来修正事件间隔。默认为False。


.. note:: 尽管WindowTurboSource继承自GenericSource，但GenericSource的direction属性中的所有参数都会失效。

表中a1、a2、b1、b2、plane_distance和plane_phi是窗口参数，它们共同定义了窗口的大小和位置。
其中a1、a2、b1、b2分别是窗口左、右、下、上的边界位置，相对的都是参考平面的中心点。
参考平面自身由plane_distance和plane_phi决定，前者是参考平面距离系统中心的距离，后者是参考平面法向量与x轴正向的夹角。
这六个量的定义方式如下图示：

.. image:: ../figures/window_turbo_source_definition.png

如果一次仿真中有多个时间间隔，则可以针对每个时间间隔定义不同的窗口参数，也可以让某几个窗口参数在所有时间间隔中保持不变。
对于每个窗口参数而言，可以是一个浮点数，也可以是一个列表。如果是一个浮点数，则在所有时间间隔中保持不变；如果是一个列表，则长度应当与仿真时间间隔的数量相同。

初始化
--------

Window Turbo Source 的位置/时间采样需要两个信息：源的所有位置中的最大立体角 max_solid_angle，以及平均而言，
有多少比例的事件可以穿过窗口 act_ratio（不考虑粒子到达窗口前发生的变化）。这两个信息也是每个仿真时间间隔都需要一组。
如果开始时提供了大于零的数值，仿真就会使用这些数值。否则的话，本源就会在每次仿真间隔前进行一次初始化，来估计这两个数值。
仿真结束之后，这两个数值也会回填到direction属性中。

.. note:: 如果使用``start_new_process=True``来运行仿真，那么回填的数值将会消失。

初始化的过程是通过源的位置采样进行的。采样的数目可以由init_sampling_count参数来定义，默认是100万。
采样的过程是并行的，线程数由init_number_of_threads参数来定义，默认与仿真线程数相同。
TBD: skip_mode参数的作用

实现细节
---------
TBD


TODO
------

体素化

Reference
---------

.. autoclass:: opengate.sources.windowturbosource.WindowTurboSource
