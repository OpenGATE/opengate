The Motivation Behind GATE 10
=============================

Background
----------

The GATE project is more than 15 years old, and it has evolved significantly over that time. The software, in its version 9.x, can perform a wide range of particle transport simulations, especially in medical physics, including various imaging systems (PET, SPECT, Compton Cameras, X-ray, etc.) and dosimetry calculations (external and internal radiotherapy, ion beam therapy, nuclear medicine, etc.). GATE has been instrumental in numerous academic research projects and industrial developments, resulting in hundreds of scientific publications since its inception.

GATE fully relies on `Geant4 <http://www.geant4.org>`_ for the Monte Carlo engine and provides:
1) easy access to Geant4 functionalities,
2) additional features (e.g., variance reduction techniques), and
3) collaborative development to share source code.

Traditionally, GATE users configured simulations using "macro" files (`.mac`). These static configuration files contained Geant4-style commands, enabling users to set up simulations without directly implementing any C++ Geant4 code. Other projects, such as Gamos or Topas, follow similar principles.

As Time Goes By
---------------

Since GATE's inception, significant changes have occurred in computer science and medical physics, including the rise of machine learning. The Python programming language has become widely used for various tasks in medical physics-oriented research and applications. Moreover, the Geant4 project remains very active and is guaranteed to be maintained for at least ten more years (as of 2020).

Despite its utility and unique features (collaborative, open-source, dedicated to medical physics), the legacy GATE software is beginning to show its age from a software development perspective. The source code has evolved over nearly 20 years, shaped by contributions from hundreds of developers. The current GitHub repository lists around 70 unique `contributors <https://github.com/OpenGATE/Gate/blob/develop/AUTHORS>`_, although this repository was only established around 2012, so early contributors are not all listed. This diversity has fostered innovation and experimentation, but it has also led to maintenance challenges. Some parts of the code are "abandoned," and others are duplicated. Additionally, the C++ language has evolved significantly over the past 20 years, introducing efficient and convenient concepts like smart pointers, lambda functions, and the `auto` keyword, which enhance code robustness and maintainability.

Towards New Frontiers
---------------------

Mindful of GATE's core principles (community-based, open-source, and oriented towards medical physics), we embarked on a project to propose a new way of performing Monte Carlo simulations in medical physics. The goal of GATE 10 is to provide a simple-to-use yet flexible Python-based interface through which users can set up Geant4 simulations. Internally, GATE 10 aims to offer developers and contributors structures and interfaces that simplify implementing and maintaining new features.

We undertook this (ambitious?) experiment, fully aware of the substantial effort it would require. Initially, we were uncertain if the goal was feasible. Today, we are proud that GATE 10 is a fully functional Monte Carlo software capable of (almost) replacing the legacy GATE 9.x code. This has been possible thanks to the group of developers who have tirelessly worked on the new software and the courageous users who tried GATE 10 at early stages and provided invaluable feedback.

Many exciting and fun features are awaiting development and implementation, so take a seat and hop on board.

Never stop exploring!

(2024)
