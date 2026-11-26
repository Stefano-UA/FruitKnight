Fruit Knight
============

**Fruit Knight** is a webcam-controlled *serious game* for upper-limb physical rehabilitation and
frailty assessment, built for the course *Interacción Persona-Máquina (IPM) mediante visión por
computador*. Players control the game with their hands in front of a camera; MediaPipe tracks
bodies and hands, Pymunk simulates the rigid bodies and Pygame CE renders everything.

Serious-game rationale
----------------------

1. **Dynamic range of motion and reaction speed (slicing fruits).** Reaching across the frame with an
   extended hand and adducted fingers exercises shoulder abduction/flexion, elbow extension and
   visuomotor reaction time.
2. **Isometric upper-limb endurance (stopping limiters).** Holding an open palm steadily against an
   advancing barrier trains isometric shoulder/arm stability and proprioceptive control.
3. **Palmar grasp rehabilitation and fine motor control (holders, Grenade v1).** Moving from open palm
   to closed fist and sustaining the grasp for a number of seconds exercises palmar flexion/extension
   and grip endurance.
4. **Ballistic coordination and kinetic-chain transfer (throwers, Grenade v2, football mode).**
   Grabbing, accelerating with a closed fist and releasing with an open palm trains coordinated reaching,
   timing and directional release.

Hand states
-----------

.. list-table::
   :header-rows: 1
   :widths: 22 38 40

   * - State
     - Recognition
     - Effect
   * - ``KNIFE_HAND``
     - Four fingers extended and adducted
     - Only state that slices fruits and detonates bombs
   * - ``OPEN_PALM``
     - Four fingers extended and spread
     - Stops a barrier limiter on its tip; ready state before grabbing
   * - ``CLOSED_FIST``
     - Fingers curled
     - Grabs the nearest entity (locks it to the palm); the hand is then occupied
   * - ``RELEASE_WITH_INERTIA``
     - Fist back to open hand while holding
     - Entity leaves with the smoothed hand velocity times ``throw_inertia_multiplier``

Game modes
----------

``1p_endurance``, ``np_endurance``, ``np_competition`` and ``2p_football``; see the project README for
the full rules, and :doc:`api` for the code reference.

Scoring
-------

.. math::

   \text{Score}_i = \sum \text{Points}_{\text{fruits},i} + N_{\text{holders},i} P_{\text{holder}}
   + N_{\text{throwers},i} P_{\text{thrower}} + \lfloor t_{\text{survived},i} M_{\text{time}} \rfloor

Football goals add ``football_goal_points`` per goal and point penalties (competition mode) subtract
``penalty_points_loss``. All weights live in ``config/settings.yaml``.

Launch kinematics
-----------------

Effective gravity is :math:`g_{\text{eff}} = g_0 w`. The launch speed reaching an apex height :math:`H`
is :math:`v_{y0} = \sqrt{2 g_{\text{eff}} H}` and :math:`v_{x0} = v_{y0}\tan\theta`, so heavier objects
move faster both when rising and when falling.

.. toctree::
   :maxdepth: 2
   :caption: Reference

   api
