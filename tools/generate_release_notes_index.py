#!/usr/bin/env python3
import os
import pathlib
import re
from collections import defaultdict
from typing import Dict, List
import yaml

import jinja2

MAJOR_VERSION = re.compile(r"(\d+)\.\d+\.\d+")
MINOR_VERSION = re.compile(r"\d+\.(\d+)\.\d+")
PATCH_VERSION = re.compile(r"\d+\.\d+\.(\d+)")
MAJOR_MINOR_VERSION = re.compile(r"(\d+\.\d+)\.\d+")


def map_post_version_sort_to_number(stem: str) -> int:
    """
    Maps the post version string (e.g. "post1" in "1.27.4.post1") to a
    number. This defines the sorting of the releases.
    """
    if re.match(".*rc\d+", stem):
        return 0
    if re.match(".*\.post\d+", stem):
        return 2
    return 1


def render_templates(templates_dir: str, output_path: pathlib.Path):
    def minor_release_get_title(path: str, version: str) -> str:
        """
        Returns the title for a minor release. If this title does not exist it
        returns the version string itself.

        :param path: The path to the folder containing the release informations.
        :param version: A major and minor version of a release. (e.g. "1.27")
        :returns: The coresponsing release title. This is just the version string in
            case no title exist.
        """

        # The minor release note title should be in the first release of the
        # minor history. Due to inconsistencies this is not always the case, so
        # we have to hardcode the missing ones.
        HARD_CODED_RELEASE_NOTE_TITLE = {
            "1.19": "1.19 Fantastic Donkeys",
            "1.13": "1.13 Donkerine"
        }
        if version in HARD_CODED_RELEASE_NOTE_TITLE:
            return HARD_CODED_RELEASE_NOTE_TITLE[version]

        release_title_file_path = os.path.join(output_path / path, version + ".0.md")

        if not os.path.exists(release_title_file_path):
            return version

        with open(release_title_file_path, 'r') as f:
            content = f.read().split("---")[1]
        data = yaml.safe_load(content)

        minor_version_title = data["title"].replace("\"", "").replace("'", "").split(".0 ")[1]
        return version + " " + minor_version_title

    def index_item(path: pathlib.Path):
        return {"stem": path.stem, "path": str(path.relative_to(output_path))}

    def index_func(path: str) -> Dict[str, List[Dict]]:
        path = output_path / path
        if not str(path).startswith(str(output_path)):
            raise ValueError("path may not escape the output path")
        if not path.exists():
            raise ValueError(f"cannot index: {path} does not exist")

        items = path.iterdir()

        mapped_items = defaultdict(list)
        for i in items:
            mapped_items[MAJOR_MINOR_VERSION.match(i.stem).group(1)].append(
                {
                    "major_version_number": int(MAJOR_VERSION.match(i.stem).group(1)),
                    "minor_version_number": int(MINOR_VERSION.match(i.stem).group(1)),
                    "patch_version_number": int(PATCH_VERSION.match(i.stem).group(1)),
                    "post_version_sort": map_post_version_sort_to_number(i.stem),
                    "stem": i.stem,
                    "path": str(i.relative_to(output_path))
                }
            )

        return mapped_items

    jinja_env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(templates_dir)
    )
    jinja_env.globals["index"] = index_func
    jinja_env.globals["minor_release_get_title"] = minor_release_get_title
    for tpl in pathlib.Path(templates_dir).iterdir():
        # render all templates with .md as the first suffix and only non-hidden files
        if tpl.suffixes[0] == ".md" and not tpl.name.startswith("."):
            jinja_template = jinja_env.get_template(str(tpl.relative_to(templates_dir)))
            tpl_out_path = output_path / tpl.name[:tpl.name.find(".md")+3]
            tpl_out_path.write_text(jinja_template.render())


if __name__ == "__main__":
    templates_dir: str = os.path.join(os.path.dirname(__file__), "templates")
    assert os.path.exists(templates_dir)
    render_templates(templates_dir, pathlib.Path(os.path.join(os.path.dirname(__file__), "../docs")).resolve())