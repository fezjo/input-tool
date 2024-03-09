# © 2014 jano <janoh@ksp.sk>
# © 2022 fezjo
"""
Format of description files:
    One line - one input
        If you end line with '\\', you can continue with next line. This action
        ignores effects of #,$,~,... on the beginning of next line.
    Inputs inside batch are named 'a-z' or 'a...a-z...z', if there are many inputs.
    Empty line separates batches.
        Batches are named 1-9 or 0..01-9..99 if there are many batches
    # starting lines are comments
    $ Overrides some behaviour until next $.
      You can use this commands in this lines, space separated
          rule=predefinedgenerator (not implemented yet)
          gen=othergenerator
          name=otherinputname
          class=prefixforname
          batch=otherbatchname
      It is your responsibility to not overwrite your own inputs with this.
    ~ starting lines will have ~ removed and no special effect applyed on them.
        Effect of '\\' will be still applyed.
    {} you can use some special variables closed inside brackets.
        {batch} - name of batch
        {name} - name of input
        {id} - 1 indexed number of this input
        {rand} - random integer from (0, MAXINT-1)
        Use {{ }} instead of single brackets or use ~ to turn of effects

"""
from __future__ import annotations

from random import randint
from typing import Any, Optional, Sequence, TextIO

import yaml

from input_tool.common.messages import error, warning


class EvalLoader(yaml.SafeLoader):
    """custom loader to allow !eval tag"""

    def __init__(self, stream: TextIO) -> None:
        super().__init__(stream)
        self.add_constructor(tag="!eval", constructor=self.evaluate)

    @staticmethod
    def evaluate(loader: yaml.Loader, node: yaml.Node) -> Any:
        # this may fail and raise an exception, this is intended
        res: Any = loader.construct_scalar(node)  # type: ignore
        try:
            res = eval(res)
            if res == int(res):
                res = int(res)
        except Exception:
            pass
        return res


def _int_log(number: int, base: int) -> int:
    result = 1
    while number >= base:
        number //= base
        result += 1
    return result


def _create_name(number: int, base: int, length: int) -> str:
    result = ""
    start = ord("0") if base == 10 else ord("a")
    for _ in range(length):
        result = chr(start + number % base) + result
        number //= base
    return result


class Input:
    maxbatch = 1
    maxid = 0
    MAXINT = 2**31

    def __lt__(self, other: Input) -> bool:
        if self.batch == other.batch:
            return self.name < other.name
        if self.batch is None:
            return True
        if other.batch is None:
            return False
        try:
            return int(self.batch) < int(other.batch)
        except ValueError:
            return self.batch < other.batch

    def __init__(self, text: str, batchid: int, subid: int, inputid: int):
        self.text = text
        self.effects = True
        self.commands: dict[str, str] = {}
        self.batchid = batchid
        self.batch: str | None = None
        self.subid = subid
        self.name: str = ""
        self.id = inputid
        self.generator: Optional[str] = None
        self.compiled = False
        Input.maxbatch = max(Input.maxbatch, batchid)
        Input.maxid = max(Input.maxid, subid)

    def _apply_commands(self) -> None:
        if not self.effects:
            return
        commands = self.commands
        self.batch = commands.get("batch", self.batch)
        self.name = commands.get("name", self.name) + commands.get("class", "")
        self.generator = commands.get("gen", self.generator)

    def _apply_format(self) -> None:
        if not self.effects:
            return
        try:
            self.text = self.text.format(
                **{
                    "batch": self.batch,
                    "name": self.name,
                    "id": self.id,
                    "rand": randint(0, Input.MAXINT - 1),
                    **self.commands,
                }
            )
        except KeyError as e:
            error(
                f"Error in filling IDF variables for input #{self.id}. "
                + f"Variable `{e.args[0]}` is undefined."
            )

    def compile(self) -> None:
        if self.compiled:
            return
        self.compiled = True
        if self.batch is None:
            self.batch = _create_name(self.batchid, 10, _int_log(Input.maxbatch, 10))
        if Input.maxid > 0:
            self.name = _create_name(self.subid, 26, _int_log(Input.maxid, 26))
        self._apply_commands()
        self._apply_format()
        if self.name:
            self.name = f".{self.name}"

    def get_name(self, path: str = "", ext: str = "") -> str:
        return "%s%s%s.%s" % (path, self.batch, self.name, ext)

    def get_generation_text(self) -> str:
        return self.text + "\n"

    def get_info_text(self, indent: int) -> str:
        prefix = "\n" + " " * indent + "<  "
        return prefix.join(self.text.split("\n"))


class Sample(Input):
    def __init__(self, lines: str, path: str, batchname: str, id: int, ext: str):
        super().__init__(lines, 0, id, id)
        self.path = path + "/"
        self.ext = ext
        self.batch = batchname
        self.effects = False

    def save(self) -> None:
        with open(self.get_name(self.path, self.ext), "w") as f:
            f.write(self.text)


class Recipe:
    def __init__(self, recipe: Sequence[str], idf_version: int = -1):
        self.recipe = recipe
        self.programs: list[str] = []
        self.inputs: list[Input] = []
        self._parse_commands_versions = [
            self._parse_commands_v0,
            self._parse_commands_v1,
            self._parse_commands_v2,
        ]
        if not -1 <= idf_version < len(self._parse_commands_versions):
            raise ValueError(f"Invalid idf_version: {idf_version}")
        self.idf_version = idf_version % len(self._parse_commands_versions)
        self._parse_commands = self._parse_commands_versions[idf_version]

    def _parse_commands_v0(self, line: str) -> dict[str, str]:
        return {}

    def _parse_commands_v1(self, line: str) -> dict[str, str]:
        commands: dict[str, str] = {}
        parts = line.split()
        for part in parts:
            if "=" in part:
                k, v = part.split("=", 1)
                commands[k] = v
                if k == "gen":
                    self.programs.append(v)
        return commands

    def _parse_commands_v2(self, line: str) -> dict[str, str]:
        line = f"{{{line}}}"
        try:
            yres = yaml.load(line, EvalLoader)
        except Exception as e:
            warning(
                f"Error parsing commands as YAML\n\tCommands: {line}\n\tError: {e!r}"
            )
            return {}
        try:
            dres = dict(yres)
            if "gen" in dres:
                self.programs.append(dres["gen"])
            if None in dres.values():
                warning(f"None value in commands\n\tCommands: {line}\n\tYAML: {yres}")
            return dres
        except Exception as e:
            warning(
                f"Error parsing YAML output as dict\n\tYAML: {yres}\n\tError: {e!r}"
            )
            return {}

    def _parse_recipe(self) -> None:
        continuingline = False
        over_commands: dict[str, str] = {}
        batchid, subid, inputid = 1, 0, 1

        for line in self.recipe:
            line = line.strip()
            if line.startswith("#"):  # comment
                if continuingline:
                    warning("Continuing line with comment, ignoring")
                    continuingline = False
                continue
            if len(line) == 0:  # new batch
                if continuingline:
                    warning("Continuing line with empty line, ignoring")
                    continuingline = False
                if subid == 0:
                    if self.idf_version == 1:  # in v1 any empty line starts new batch
                        warning(f"Empty batch #{batchid}, maybe excessive empty line?")
                    else:
                        continue  # superfluous empty lines are ignored
                batchid += 1
                subid = 0
                continue

            add_to_previous = continuingline
            continuingline = line.endswith("\\")
            if continuingline:
                line = line[:-1]
            if add_to_previous:
                self.inputs[-1].text += "\n" + line
                continue

            if line.startswith("$+"):
                new_commands = self._parse_commands(line[2:])
                over_commands = dict(over_commands, **new_commands)
                continue
            if line.startswith("$"):
                over_commands = self._parse_commands(line[1:])
                continue

            effects = True
            if line.startswith("~"):  # effects off
                line = line[1:]
                effects = False

            self.inputs.append(Input(line, batchid, subid, inputid))
            subid += 1
            inputid += 1
            self.inputs[-1].effects = effects
            self.inputs[-1].commands = over_commands

    def process(self) -> None:
        self._parse_recipe()
        for input in self.inputs:
            input.compile()


_cumberbatch = """\
~~~~~~~~~~~~~~~~~~~+::=~:~=,~~~:=+=~~~~~~~~~~~~~~~~~~~~~~~~~
~~~~~~~~~~~~~~:~==~:+::===::::,..,:~~+~~~~~~~~~~~~~:~:::~~~~
::~~~~~~~~~~~~==:~~~.::~~,~,~,:====~:~=~~~~~~~~~~~:::::::~~~
::~~~~~~~~~~~~:~:~~:,::~,,==::~:,.,,.~:~~:::~~~~~~~~~~~~~~~~
~~~~~::~~~~~::~~::::,,:,,:~~:::=~::~~~=::~~~:=~~~~~~~~~~~~~~
===~~~~~=~~~:~,:,::,,:,,:,,,,,:,:,,,,,:~,::,,,:~:==~~~~~~~~~
==~~~~~~~~~,~,:.,,,.:,,:,,:,,,...,,,,,,,,,,,,..,~=+=~~~~~~=~
~~~~~~~:::,::,,,,,~:::,,,.,,,,,,...,,,::,,.,.,.,:~:~~~~~~~~~
~~~::=:~:~~:,:.,,,,,,,.::,...,.,....,~??=..,..,.,~:=====~~~~
:~~~:~~:::~::,,,,..:.,,.:,,,,..,:===??II?+,..,.,.,::~=~~~~~~
:::::,:::,,,,......,,.,.,,....,~++??IIIII?=..,.,,,::~=~~~~~~
::::~~,,,,..,......,,,,,.,,...:++???IIIIIII:..,:,,::~+=~~~~~
~~~:~:,,,,.,......,:..,,~=,,,,~+????IIIII7I+,,.....,~+~~~~~~
~~~~:,,,,,.......,~+++====~~~~++????I?IIIII+:.,....,,,:=~~~~
~~~~:,,.......,.,~=+++++++++++++???I?I?III?+:.....,,,,,~~~~~
::~:,,,.....,.,,,~=+?????????????IIIIIIIII?+:......,:,,,~~~~
:~~:,......,...,~=++???????????IIII??II??II?=........,,:~~~~
~~~:,..........,==+?????????????I?????II???I+.......,,,~~~~~
~~~:,..........:=+=~~~====+++?=++===+=~~::~=+,......:::====~
~~~:::.........~=+=~=~~~:::::~~++~:::,,,,,~=?=,,...::~~~==~~
::::~:,,..,:,,,=++++==~::::,~~???+~:~~~==+?+?=,:...,~~~~~~~~
::::~:,...::,,:=++??+++=======?III=+===++????+,:,,::~~::~:::
:::::::,..,=:~,:++??????+++?+??III?+??++?????~+=::::::::::::
:::::::::..=++=~=+?????????????III?????????++++,~:::~~~~::~~
:::::::~:,..===+=+++????????+I?IIII?=+????+=++~,:~~~~~~~~~~~
::::::::::.,,.~~=====+????+~????????+=+?+++=:.:,~~~=========
::::::::::::,,:.++++=++++=~=~:,~~~,,==~=++++.::,~~~~~~~~~~~~
:~~~~~~~~~~~~~,.==++++++===++==~:~~=====++++.,,,:~~~~~~~~~~~
::~:::::~~::~~...+=+++++===+++=~~~===~===++?.,,,::,~~~~~~~~~
::::::::~:::::,..===+=++=~:~+++=+=~==::~==+:.:,,,,::~~~~~~~~
::::::~~~::::,,..=~~====~~====~,,~=++======.,::..,:,:::~~~~~
:::::~:~:::::,,,.:~~~~~~==++++?+++===++=~~:.,,:,..,,:,:,~~~~
~~:~~~~~~~~~:,,,,.~:::::~=++=~~:~:~~=====:.,,:::...,,,,,,=~~
~~~~~~~~~~~~,,,,,.:~:::~~=+===========+=~,.,,:::..,,.:.,~,:~
~~~:~~~~~~~~,,,,,.,:~,::~~=+++???+++++=~..,,,,::...,.,,,::,:
~~~~~~~~~~~~.,,,...:~~,,:::=++=====~==~...,,,,::,....,,,,,,,
~~~~:~~~~~~:,,,,....:~~:,,,:::~:::::,.....,,,,,:,..,,,,,,,,,
~~~~~~:~~~:,,,,,.....:~~~~:,,,,,,,,,.....,,,,,,,,..,,,,,,,:,
~~~~~~::::,::,.,.....:::~~:~::,,,,,.....,,,,,,,,,,,,,,,,,:,:"""


def prepare_cumber(batchname: str) -> None:
    # lol ;)
    if batchname.lower() == "cumber":
        print(_cumberbatch)
