import opengate_core as g4
import opengate as gate
import threading


class ActionEngine(g4.G4VUserActionInitialization, gate.EngineBase):
    """
    Main object to manage all actions during a simulation.
    """

    def __init__(self, simulation_engine):
        g4.G4VUserActionInitialization.__init__(self)
        gate.EngineBase.__init__(self, simulation_engine)

        # The py source engine
        # self.simulation_engine.source_engine = source
        self.simulation_engine = simulation_engine

        # *** G4 references ***
        # List of G4 source managers (one per thread)
        self.g4_PrimaryGenerator = []

        # The main G4 source manager
        self.g4_main_PrimaryGenerator = None

        # Lists of elements to prevent destruction
        self.g4_RunAction = []
        self.g4_EventAction = []
        self.g4_TrackingAction = []

    def __del__(self):
        if self.verbose_destructor:
            gate.warning("Deleting ActionEngine")

    def close(self):
        if self.verbose_close:
            gate.warning(f"Closing ActionEngine")
        self.release_g4_references()

    def release_g4_references(self):
        self.g4_PrimaryGenerator = None
        self.g4_main_PrimaryGenerator = None
        self.g4_RunAction = None
        self.g4_EventAction = None
        self.g4_TrackingAction = None

    def BuildForMaster(self):
        # This function is call only in MT mode, for the master thread
        if not self.g4_main_PrimaryGenerator:
            self.g4_main_PrimaryGenerator = (
                self.simulation_engine.source_engine.create_master_source_manager()
            )

    def Build(self):
        # In MT mode this Build function is invoked
        # for each worker thread, so all user action classes
        # are defined thread-locally.

        # If MT is not enabled, need to create the main source
        if not self.g4_main_PrimaryGenerator:
            p = self.simulation_engine.source_engine.create_master_source_manager()
            self.g4_main_PrimaryGenerator = p
        else:
            # else create a source for each thread
            p = self.simulation_engine.source_engine.create_g4_source_manager()

        self.SetUserAction(p)
        self.g4_PrimaryGenerator.append(p)

        # set the actions for Run
        ra = g4.GateRunAction(p)
        self.SetUserAction(ra)
        self.g4_RunAction.append(ra)

        # set the actions for Event
        ea = g4.GateEventAction()
        self.SetUserAction(ea)
        self.g4_EventAction.append(ea)

        # set the actions for Track
        ta = g4.GateTrackingAction()
        ta.fUserEventInformationFlag = (
            self.simulation_engine.user_event_information_flag
        )
        self.SetUserAction(ta)
        self.g4_TrackingAction.append(ta)
