.. _source-window-turbo-source:
Window Turbo Source
=====================

开发目标
--------
首先实现一个最简化版本，做以下约束
1. 不支持一个``sim.run()``中多个run interval。
2. 不支持体素化源
3. 支持两种不同的skip_mode。
4. 不支持生成光子数n的定义

Description
-----------

Direction
---------
尽管本模块继承自"GenericSource"，但在方向定义上，本模块不支持除了以下列表中的项目以外的一切参数：

.. list-table::
    :header-rows: 1
    * - **参数** - **描述**
    * - ``a1`` - 窗口左边界，见图1
    * - ``a2`` - 窗口右边界，见图1
    * - ``b1`` - 窗口下边界，见图1
    * - ``b2`` - 窗口上边界，见图1
    * - ``plane_distance`` - 窗口平面距离系统中心的距离，见图1
    * - ``plane_phi`` - 窗口法向量与x轴正向的夹角，见图1
    * - ``init_sampling_count`` - 初始化阶段的采样数量，默认为100万
    * - ``init_number_of_threads`` - 初始化阶段的线程数量，默认与仿真线程数量相同
    * - ``act_ratio`` - 活度比例，由初始化得到。默认为nan。
    * - ``max_solid_angle`` - 最大立体角，由初始化得到。默认为nan。
    * - ``skip_mode`` - 是否采用跳过模式。采用跳过模式，则事件间隔依靠前一个事件的立体角来修正；否则则会计算一个总体的活度比例来修正事件间隔。默认为False。
