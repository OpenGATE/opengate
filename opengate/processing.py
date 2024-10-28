import multiprocessing
import queue
import numpy as np
import tqdm
import uproot

from .exception import fatal
from .base import GateObject


# define thin wrapper function to handle the queue
def target_func(q, f, *args, **kwargs):
    q.put(f(*args, **kwargs))


def dispatch_to_subprocess(func, *args, **kwargs):
    try:
        multiprocessing.set_start_method("spawn")
    except RuntimeError:
        pass

    q = multiprocessing.Manager().Queue()
    # FIXME: would this also work?
    # q = multiprocessing.Queue()
    p = multiprocessing.Process(
        target=target_func, args=(q, func, *args), kwargs=kwargs
    )
    p.start()
    p.join()  # (timeout=10)  # timeout might be needed

    try:
        return q.get(block=False)
    except queue.Empty:
        fatal("The queue is empty. The spawned process probably died.")


def _setter_hook_number_of_processes(self, number_of_processes):
    if self.number_of_processes != number_of_processes:
        self._dispatch_configuration = {}
        self.process_run_index_map = {}
        self.inverse_process_to_run_index_map = {}
    return number_of_processes


class MultiProcessingHandlerBase(GateObject):

    user_info_defaults = {
        "number_of_processes": (
            1,
            {
                "doc": "In how many parallel process should the simulation be run? "
                "Must be a multiple of the number of run timing intervals. ",
                "setter_hook": _setter_hook_number_of_processes,
            },
        )
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._dispatch_configuration = {}
        self.process_run_index_map = {}
        self.inverse_process_to_run_index_map = {}

    @property
    def original_run_timing_intervals(self):
        return self.simulation.run_timing_intervals

    @property
    def dispatch_configuration(self):
        return self._dispatch_configuration

    @dispatch_configuration.setter
    def dispatch_configuration(self, config):
        self._dispatch_configuration = config
        self.update_process_to_run_index_maps()

    def assert_dispatch_configuration(self):
        if self.dispatch_configuration is None or len(self.dispatch_configuration) == 0:
            fatal("No dispatch configuration is available. ")

    def initialize(self):
        self.generate_dispatch_configuration()

    def get_original_run_timing_indices_for_process(self, process_index):
        return self.dispatch_configuration[process_index]["lut_original_rti"]

    def get_run_timing_intervals_for_process(self, process_index):
        return self.dispatch_configuration[process_index]["run_timing_intervals"]

    def generate_dispatch_configuration(self):
        raise NotImplementedError

    def update_process_to_run_index_maps(self):
        """Creates a mapping (process index, local run index) -> (original run index)"""
        self.assert_dispatch_configuration()

        p_r_map = {}
        for k, v in self.dispatch_configuration.items():
            for lri, ori in enumerate(v["lut_original_rti"]):
                p_r_map[(k, lri)] = ori

        # and the inverse
        p_r_map_inv = dict([(i, []) for i in set(p_r_map.values())])
        for k, v in p_r_map.items():
            p_r_map_inv[v].append(k)

        self.process_run_index_map = p_r_map
        self.inverse_process_to_run_index_map = p_r_map_inv

    def dispatch_to_processes(self, dispatch_function, *args):
        return [
            dispatch_function(i, *args) for i in range(len(self.dispatch_configuration))
        ]


class MultiProcessingHandlerEqualPerRunTimingInterval(MultiProcessingHandlerBase):

    def generate_dispatch_configuration(self):
        if self.number_of_processes % len(self.original_run_timing_intervals) != 0:
            fatal(
                "number_of_sub_processes must be a multiple of the number of run_timing_intervals, \n"
                f"but I received {self.number_of_processes}, while there are {len(self.original_run_timing_intervals)}."
            )

        number_of_processes_per_run = int(
            self.number_of_processes / len(self.original_run_timing_intervals)
        )
        dispatch_configuration = {}
        process_index = 0
        for i, rti in enumerate(self.original_run_timing_intervals):
            t_start, t_end = rti
            duration_original = t_end - t_start
            duration_in_process = duration_original / number_of_processes_per_run
            t_intermediate = [
                t_start + (j + 1) * duration_in_process
                for j in range(number_of_processes_per_run - 1)
            ]
            t_all = [t_start] + t_intermediate + [t_end]
            for t_s, t_e in zip(t_all[:-1], t_all[1:]):
                dispatch_configuration[process_index] = {
                    "run_timing_intervals": [[t_s, t_e]],
                    "lut_original_rti": [i],
                    "process_id": None,
                }
                process_index += 1
        self.dispatch_configuration = dispatch_configuration
        return dispatch_configuration

def unicity(root_keys):
    """
    Return an array containing the keys of the root file only one (without the version number)
    """
    root_array = []
    for key in root_keys:
        name = key.split(";")
        if len(name) > 2:
            name = ";".join(name)
        else:
            name = name[0]
        if name not in root_array:
            root_array.append(name)
    return root_array


def merge_root(rootfiles, outputfile, increment_run_id=False):
    """
    Merge root files in output files
    """

    uproot.default_library = "np"

    out = uproot.recreate(outputfile)

    # Previous ID values to be able to increment runIn or EventId
    previous_id = {}

    # create the dict reading all input root files
    trees = {}  # TTree with TBranch
    hists = {}  # Directory with THist
    pbar = tqdm.tqdm(total=len(rootfiles))
    for rf in rootfiles:
        root = uproot.open(rf)
        tree_names = unicity(root.keys())
        for tree_name in tree_names:
            if hasattr(root[tree_name], 'keys'):
                if tree_name not in trees:
                    trees[tree_name] = {"rootDictType": {}, "rootDictValue": {}}
                    hists[tree_name] = {"rootDictType": {}, "rootDictValue": {}}
                    previous_id[tree_name] = {}
                for branch in root[tree_name].keys():
                    if isinstance(root[tree_name], uproot.reading.ReadOnlyDirectory):
                        print(branch)
                        array = root[tree_name][branch].values()
                        if len(array) > 0:
                            branch_name = tree_name + "/" + branch
                            if isinstance(array[0], str):
                                array = np.zeros(len(array))
                            if branch_name not in hists[tree_name]["rootDictType"]:
                                hists[tree_name]["rootDictType"][branch_name] = root[tree_name][branch].to_numpy()
                                hists[tree_name]["rootDictValue"][branch_name] = np.zeros(len(array))
                            hists[tree_name]["rootDictValue"][branch_name] += array
                    else:
                        array = root[tree_name][branch].array(library="np")
                        if len(array) > 0 and not isinstance(array[0], np.ndarray):
                            if isinstance(array[0], str):
                                array = np.zeros(len(array))
                            if branch not in trees[tree_name]["rootDictType"]:
                                trees[tree_name]["rootDictType"][branch] = type(array[0])
                                trees[tree_name]["rootDictValue"][branch] = np.array([])
                            if (not increment_run_id and branch.startswith('eventID')) or (
                                    increment_run_id and branch.startswith('runID')):
                                if branch not in previous_id[tree_name]:
                                    previous_id[tree_name][branch] = 0
                                array += previous_id[tree_name][branch]
                                previous_id[tree_name][branch] = max(array) + 1
                            trees[tree_name]["rootDictValue"][branch] = np.append(
                                trees[tree_name]["rootDictValue"][branch], array)
        pbar.update(1)
    pbar.close()

    # Set the dict in the output root file
    for tree_name in trees:
        if not trees[tree_name]["rootDictValue"] == {} or not trees[tree_name]["rootDictType"] == {}:
            # out.mktree(tree, trees[tree]["rootDictType"])
            out[tree_name] = trees[tree_name]["rootDictValue"]
    for hist in hists.values():
        if len(hist["rootDictValue"]) > 0 and len(hist["rootDictType"]) > 0:
            for branch in hist["rootDictValue"]:
                for i in range(len(hist["rootDictValue"][branch])):
                    hist["rootDictType"][branch][0][i] = hist["rootDictValue"][branch][i]
                out[branch[:-2]] = hist["rootDictType"][branch]
