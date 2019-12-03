import configparser
import subprocess
import sys
from pathlib import Path

from appdirs import AppDirs
from tqdm import tqdm

try:
    import ujson as json
except ImportError:
    import json

dirs = AppDirs("hardware")
inifile = Path(dirs.user_config_dir) / "config.ini"
cachedir = Path(dirs.user_cache_dir)

config = configparser.ConfigParser()
config.read(inifile)


def get_data_dir():
    try:
        path = config.get("Paths", "data").replace('"', "")
        path = path.replace("'", "")
        path = Path(path)
    except (configparser.NoOptionError, configparser.NoSectionError):
        path = None
        print()
        print("No data path found, please add it to {}".format(inifile))
        print("   The file should contain something like:")
        print("       [Paths]")
        print("       data = <path to data>")
        print()
    return path


def iterate_pairs(mylist):
    """Go through an iterable and return the current item and the next"""

    if len(mylist) < 2:
        return
    for i, d in enumerate(mylist[:-1]):
        yield mylist[i], mylist[i + 1]
    return


def iterate_N(mylist, number=2):
    """Go through an iterable and return several items at once,
    but still go through each item as the first in a list"""

    if len(mylist) < number:
        return
    for i, d in enumerate(mylist[: -number + 1]):
        yield [k for k in mylist[i : i + number]]
    return


def group_N(mylist, number=2):
    """Go through an iterable and return several items at once"""

    if len(mylist) < number:
        return
    for i, d in enumerate(mylist[: 1 - number : number]):
        yield [k for k in mylist[i * number : i * number + number]]
    return


def find_file(name, local_only=False):
    """Look for a data file in different places"""

    data_dir = get_data_dir()
    if data_dir is None:
        print("Error: can't find data dir")
        sys.exit(1)

    # first check if the data is directly in the directory
    test = data_dir / name
    if test.exists() and test.is_file():
        return test

    # search in data_dir for file
    result = list(data_dir.glob(f"**/{name}"))
    if len(result) == 0:
        print(f"Could not find file {name} in {data_dir}")
        if local_only:
            return None
        print("Checking google")
        found = find_file_drive(name)
        return found
    elif len(result) == 1:
        return result[0]
    else:
        print(f"more than one match for {name}")
        print(f"using {result[0]}")
        return result[0]


def find_file_drive(name):
    """Check if we can find the file on google drive"""

    data_dir = get_data_dir()
    if data_dir is None:
        print("Error: can't find data dir")
        sys.exit(1)

    drive_update_listing()
    mydirs = cachedir.glob("root-data-*")
    found = None
    founddir = None
    print("Checking google cache for file")
    for m in mydirs:
        with m.open() as f:
            tmp = json.load(f)
        for i in tmp:
            if name == i:
                d = m.name
                d = d[10:-5]

                found = f"{d}/{i}"
                founddir = d
                break

    if found:
        print("downloading file", found)
        # download file
        out = subprocess.check_output(
            f"rclone copy hardware_control:Data/{found} {data_dir}/{founddir}/",
            stderr=subprocess.STDOUT,
            shell=True,
        )
        return f"{data_dir}/{found}"
    return None


def drive_update_listing():
    """Get all files in the google drive directory 'dir'

    We store locally the listing of the main directory with it's modification time.
    We always fetch this listing new and then only fetch the subdirectories
    new that have a newer modification time.

    """
    # ensure directory exists
    cachedir.mkdir(parents=True, exist_ok=True)

    root_dir = cachedir / "root-data.json"
    if root_dir.exists():
        with root_dir.open() as f:
            old = json.load(f)
    else:
        old = None

    print("Updating google cache")
    out = subprocess.check_output(
        "rclone lsjson --fast-list --drive-skip-gdocs hardware_control:Data",
        stderr=subprocess.STDOUT,
        shell=True,
    )

    datatmp = json.loads(out)

    # we reformat the data a bit, so that lookup is easier. We also only need the ModTime
    data = {}
    for i in datatmp:
        if i["IsDir"]:
            data[i["Path"]] = i["ModTime"]

    # always save data
    with root_dir.open("w") as f:
        json.dump(data, f)

    # if the timestamp didn't change, we don't need to update the listing
    needs_update = []
    if old is not None:
        for p, t in data.items():
            if p not in old:
                needs_update.append(p)
            else:
                if t > old[p]:
                    needs_update.append(p)
    else:
        needs_update = list(data)

    # return if nothing to do, fixes extra output from tqdm
    if not needs_update:
        return

    # next we download listings for all directories
    for d in tqdm(needs_update):
        mydir = cachedir / f"root-data-{d}.json"
        out = subprocess.check_output(
            f"rclone lsjson -R --fast-list --drive-skip-gdocs hardware_control:Data/{d}",
            stderr=subprocess.STDOUT,
            shell=True,
        )

        datatmp = json.loads(out)
        # we reformat the data a bit, so that lookup is easier. We also only need the ModTime
        data = {}
        for i in datatmp:
            data[i["Path"]] = i["ModTime"]

        # always save data
        with mydir.open("w") as f:
            json.dump(data, f)
