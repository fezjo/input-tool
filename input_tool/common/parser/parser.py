# © 2014 jano <janoh@ksp.sk>
# © 2022 fezjo
import argparse
from importlib.metadata import version
from typing import Sequence, Type, TypeVar

import argcomplete

import input_tool.common.parser.specifications as specs
from input_tool.common.parser.options import argument_options


def MyHelpFormatterFactory(_full_mode: bool) -> Type[argparse.HelpFormatter]:
    class MyHelpFormatter(argparse.HelpFormatter):
        # options with help message starting with this prefix are considered secondary
        # secondary options are only printed in full help mode
        # primary options in full help mode are printed in bold
        mode_prefix = "[?]"
        full_mode = _full_mode

        def _format_action_invocation(self, action):
            if not action.option_strings:
                default = self._get_default_metavar_for_positional(action)
                (metavar,) = self._metavar_formatter(action, default)(1)
                return metavar

            else:
                options = sorted(action.option_strings, key=len)
                if len(options[0]) != 2:  # align long only options
                    options = ["  "] + options
                res = "  ".join(options)

                if action.nargs != 0:
                    default = self._get_default_metavar_for_optional(action)
                    args_string = self._format_args(action, default)
                    res += " " + args_string

                return res

        def _format_action(self, action):
            if action.help is None:
                return super()._format_action(action)
            orig_help = action.help
            issecondary = action.help.startswith(self.mode_prefix)
            if issecondary:
                action.help = action.help.removeprefix(self.mode_prefix).strip()
            res = ""
            if self.full_mode or not issecondary:
                res = super()._format_action(action)
            action.help = orig_help
            if self.full_mode and not issecondary:
                if res.endswith("\n"):
                    res = res[:-1]
                res = f"\033[1m{res}\033[0m\n"
            return res

    return MyHelpFormatter


class Parser:
    def __init__(self, description: str, arguments: Sequence[str]):
        self.parser = argparse.ArgumentParser(
            description=description,
            formatter_class=MyHelpFormatterFactory(False),
            add_help=False,
        )
        self.fh_parser = argparse.ArgumentParser(
            description=description,
            formatter_class=MyHelpFormatterFactory(True),
            add_help=False,
        )
        groups = {
            name: self.fh_parser.add_argument_group(name)
            for name in (
                "actions",
                "naming",
                "preparing",
                "verbosing",
                "cleaning",
                "generating",
                "testing",
                "running",
            )
        }

        for arg in arguments:
            full_parser_group: (
                argparse.ArgumentParser | argparse._ArgumentGroup
            ) = self.fh_parser
            args, kwargs, group = argument_options.get(arg, (None, None, None))
            if args is None or kwargs is None:
                raise NameError(f"Unrecognized option {arg}")
            if group is not None and group:
                if group not in groups:
                    raise NameError(f"Unrecognized group {group}")
                full_parser_group = groups[group]
            if "default" in kwargs and "help" in kwargs:
                kwargs["help"] = kwargs["help"].format(kwargs["default"])
            full_parser_group.add_argument(*args, **kwargs)
            self.parser.add_argument(*args, **kwargs)

    Args = TypeVar("Args", specs.ArgsSample, specs.ArgsGenerator, specs.ArgsTester)

    def parse(self, container: Type[Args]) -> Args:
        argcomplete.autocomplete(self.parser)
        self.args = self.parser.parse_args()
        if self.args.full_help:
            self.fh_parser.print_help()
            quit(0)
        return container(**vars(self.args))


class UnifiedParser:
    def __init__(self):
        self.parser = argparse.ArgumentParser(
            "itool",
            description="Input Tool -- Tool which simplifies creating and testing "
            + "inputs for programming contests.",
            formatter_class=MyHelpFormatterFactory(False),
        )
        self.parser.add_argument(
            "--version", action="version", version=version("input-tool")
        )
        self.subparsers = self.parser.add_subparsers(dest="subcommand")

        self.sample_parser, self.sample_fh_parser = self.add_subparser(
            "sample",
            ("s",),
            specs.description_sample,
            specs.short_description_sample,
            specs.options_sample,
        )
        self.generator_parser, self.generator_fh_parser = self.add_subparser(
            "generate",
            ("g",),
            specs.description_generator,
            specs.short_description_generator,
            specs.options_generator,
        )
        self.tester_parser, self.tester_fh_parser = self.add_subparser(
            "test",
            ("t",),
            specs.description_tester,
            specs.short_description_tester,
            specs.options_tester,
        )
        self.compile_parser, self.compile_fh_parser = self.add_subparser(
            "compile",
            ("c",),
            specs.description_compile,
            specs.short_description_compile,
            specs.options_compile,
        )
        self.autogenerate_parser, self.autogenerate_fh_parser = self.add_subparser(
            "autogenerate",
            ("ag",),
            specs.description_autogenerate,
            specs.short_description_autogenerate,
            specs.options_autogenerate,
        )
        self.colortest_parser, self.colortest_fh_parser = self.add_subparser(
            "colortest",
            (),
            specs.description_colortest,
            specs.short_description_colortest,
            ["help"],
        )
        self.checkupdates_parser, self.checkupdates_fh_parser = self.add_subparser(
            "checkupdates",
            (),
            specs.description_checkupdates,
            specs.short_description_checkupdates,
            ["help"],
        )

        self.alias_mapping = {
            "sample": "sample",
            "s": "sample",
            "generate": "generate",
            "g": "generate",
            "test": "test",
            "t": "test",
            "compile": "compile",
            "c": "compile",
            "autogenerate": "autogenerate",
            "ag": "autogenerate",
            "colortest": "colortest",
            "checkupdates": "checkupdates",
        }
        self.mapping = {
            "sample": (
                self.sample_parser,
                self.sample_fh_parser,
                specs.ArgsSample,
            ),
            "generate": (
                self.generator_parser,
                self.generator_fh_parser,
                specs.ArgsGenerator,
            ),
            "test": (
                self.tester_parser,
                self.tester_fh_parser,
                specs.ArgsTester,
            ),
            "compile": (
                self.compile_parser,
                self.compile_fh_parser,
                specs.ArgsCompile,
            ),
            "autogenerate": (
                self.autogenerate_parser,
                self.autogenerate_fh_parser,
                specs.ArgsAutogenerate,
            ),
            "colortest": (
                self.colortest_parser,
                self.colortest_fh_parser,
                argparse.Namespace,
            ),
            "checkupdates": (
                self.checkupdates_parser,
                self.checkupdates_fh_parser,
                argparse.Namespace,
            ),
        }

    # TODO refactor against Parser
    def add_subparser(
        self,
        title: str,
        aliases: Sequence[str],
        description: str,
        short_description: str,
        arguments: list[str],
    ) -> tuple[argparse.ArgumentParser, argparse.ArgumentParser]:
        parser = self.subparsers.add_parser(
            name=title,
            help=short_description,
            aliases=aliases,
            description=description,
            formatter_class=MyHelpFormatterFactory(False),
            add_help=False,
        )
        fh_parser = argparse.ArgumentParser(
            description=description,
            formatter_class=MyHelpFormatterFactory(True),
            add_help=False,
        )
        groups = {
            name: fh_parser.add_argument_group(name)
            for name in (
                "actions",
                "naming",
                "preparing",
                "verbosing",
                "cleaning",
                "generating",
                "testing",
                "running",
            )
        }

        for arg in arguments:
            full_parser_group: (
                argparse.ArgumentParser | argparse._ArgumentGroup
            ) = fh_parser
            args, kwargs, group = argument_options.get(arg, (None, None, None))
            if args is None or kwargs is None:
                raise NameError(f"Unrecognized option {arg}")
            if group is not None and group:
                if group not in groups:
                    raise NameError(f"Unrecognized group {group}")
                full_parser_group = groups[group]
            if "default" in kwargs and "help" in kwargs:
                kwargs["help"] = kwargs["help"].format(kwargs["default"])
            full_parser_group.add_argument(*args, **kwargs)
            parser.add_argument(*args, **kwargs)

        return (parser, fh_parser)

    def parse(self) -> tuple[str, specs.Args]:
        argcomplete.autocomplete(self.parser)
        args = self.parser.parse_args()
        subcommand = args.subcommand
        if subcommand is None:
            self.parser.print_help()
            quit(0)
        if subcommand not in self.alias_mapping:
            raise NameError(f"Unrecognized subcommand {subcommand}")
        subcommand = self.alias_mapping[subcommand]
        (_, fh_parser, container) = self.mapping[subcommand]
        delattr(args, "subcommand")
        args = container(**vars(args))
        if hasattr(args, "full_help") and args.full_help:
            fh_parser.print_help()
            quit(0)
        return subcommand, args
