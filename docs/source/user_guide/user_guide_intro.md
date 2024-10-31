# The motivation behind GATE 10

## Background

The GATE project is more than 15 years old, and it has evolved a lot during that period. The software in its version 9.x  can perform a wide range of particle transport simulations, especially in the field of medical physics, including various imaging systems (PET, SPECT, Compton Cameras, X-ray, etc.) and dosimetry calculations (external and internal radiotherapy, ion beam therapy, nuclear medicine etc.). GATE has served in many projects in academic research and industrial development and hundreds of scientific publications have emerged since its first version.

GATE fully relies on [Geant4](http://www.geant4.org) for the Monte Carlo engine and provides 1) easy access to Geant4 functionalities, 2) additional features (e.g. variance reduction techniques) and 3) collaborative development to share source code. Traditionally, GATE users had to set up simulations via so-called `macro` files (`.mac`). These static configuration files contained Geant4-style commands via which a user sets-up a simulation without directly implementing any C++ Geant4 code. Other projects such as Gamos or Topas also rely on similar principles.

## As time goes by
Since the beginning of GATE, a lot of changes have happened in the fields of computer science and medical physics, with, among others, the rise of machine learning. The Python programming language is now widely used for various tasks in medical physics oriented research and applications. Finally, the Geant4 project continues to be very active and is guaranteed to be maintained for at least ten more years (as of 2020).

Despite its usefulness and its unique features (collaborative, open source, dedicated to medical physics), we think that the legacy GATE software is showing its age, from a computer science and software development point of view. The source code has been worked on for almost 20 years by literally hundreds of different developers. The current GitHub repository indicates around 70 unique [contributors](https://github.com/OpenGATE/Gate/blob/develop/AUTHORS), but it has been set up only around 2012 and a lot of early contributors are not mentioned in this list. This diversity is the source of a lot of innovation and experiments (and fun!), but also leads to maintenance issues. Some parts of the code are "abandoned", some others are somehow duplicated. Also, the C++ language standard has evolved tremendously during the last 20 years, with very efficient and convenient concepts such as smart pointers, lambda functions, 'auto' keyword, etc., that make C++ code more robust and easier to write and maintain.

## Towards new frontiers
Keeping in mind the core pillars of GATE's  principles (community-based, open-source, medical physics oriented), we decided to start a project to propose a new way of performing Monte Carlo simulations in medical physics.
The goal of GATE 10 is to provide a simple-to-use yet flexible Python-based interface to the user through which Geant4 simulations can be set up. Internally, GATE 10 aims to provide developers and contributors with structures and interfaces that make implementing and maintaining new feature as simple as possible.

We took off into this (crazy?) experiment, well aware of the huge effort it would require to complete it. At the beginning, we were not sure if the goal was feasible. Today, we are proud that GATE 10 is a fully functional Monte Carlo software that can (almost) replace the legacy Gate 9.x code. This has become possible not only thanks to the group of developers tirelessly working on the new software, but also thanks to audacious users who have tried the new GATE 10 even at an early stage and have provided valuable feedback.

There are plenty of exciting and fun features waiting to be developed and implemented, so take a seat and hope on board.

Never stop exploring !

(2024)

[//]: # ()
[//]: # (### Goals and features)

[//]: # ()
[//]: # ([//]: # &#40;The main goal of this project is to provide easy and flexible way to create Geant4-based Monte Carlo simulations for **medical physics**. User interface is completely renewed so that simulations are no more created from macro files but directly in Python.&#41;)
[//]: # ([//]: # &#40;Features:&#41;)
[//]: # ([//]: # &#40;- Python as 'macro' language&#41;)
[//]: # ([//]: # &#40;- Multithreading&#41;)
[//]: # ([//]: # &#40;- Native ITK image management&#41;)
[//]: # ([//]: # &#40;- Run on linux, mac &#40;and potentially, windows&#41;&#41;)
[//]: # ([//]: # &#40;- Install with one command &#40;`pip install opengate`&#41;&#41;)
[//]: # ()
[//]: # (The purpose of this software is to facilitate the creation of Geant4-based Monte Carlo simulations for medical physics using Python as the primary scripting language. The user interface has been redesigned to allow for direct creation of simulations in Python, rather than using macro files.)

[//]: # ()
[//]: # (Some key features of this software include:)

[//]: # ()
[//]: # (- Use of Python as the primary scripting language for creating simulations)

[//]: # (- Multithreading support for efficient simulation execution)

[//]: # (- Native integration with ITK for image management)

[//]: # (- Compatibility with Linux, Mac, and potentially Windows operating systems)

[//]: # (- Convenient installation via a single pip install opengate command)

[//]: # (- ...)

