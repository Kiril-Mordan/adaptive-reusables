"""
This module contains methods to clean up llm generated and adapted workflows 
by turning all literal inputs produced by llm into a populated input model for
the workflow.
"""

import attrs
import attrsx

import re
from typing import Any
import copy


@attrsx.define()
class InputCollector:

    def _extract_leaf_paths(self, data: any, prefix: str = "") -> dict:
        """
        Recursively traverse a nested structure (dicts and lists) and return a dictionary
        mapping each leaf's full path to its value, but skipping any leaves whose key is "name".

        For example, given:
        {
        'name': 'get_weather',
        'args': {'city': 'Berlin'}
        }
        It returns:
        {
        "args.city": "Berlin"
        }
        
        For lists, the index is included in square brackets. For example:
        {
        'information': [
            {'title': 'Weather Forecast', 'content': 'source: get_weather.output.condition'}
        ]
        }
        Would yield:
        {
        "information[0].title": "Weather Forecast",
        "information[0].content": "source: get_weather.output.condition"
        }
        """
        leaves = {}
        
        if isinstance(data, dict):
            for key, value in data.items():
                # Skip the key if it is "name"
                if key == "name":
                    continue
                new_prefix = f"{prefix}.{key}" if prefix else key
                leaves.update(self._extract_leaf_paths(value, new_prefix))
        elif isinstance(data, list):
            for idx, item in enumerate(data):
                new_prefix = f"{prefix}[{idx}]"
                leaves.update(self._extract_leaf_paths(item, new_prefix))
        else:
            # If the final key is "name", skip adding it.
            if not prefix.endswith(".name") and prefix != "name":
                leaves[prefix] = data
            
        return leaves

    def _set_by_path(self, data: any, path: str, value: any) -> any:
        """
        Return a modified copy of a nested structure (dicts/lists) given a path string.
        
        The path format uses dots to separate keys and [index] for list indices.
        For example: "[2].args.information[1].content"
        """
        new_data = copy.deepcopy(data)
        parts = re.split(r'\.(?![^\[]*\])', path)
        current = new_data
        for i, part in enumerate(parts):
            # Extract any list indices at the beginning of the part.
            while part.startswith('['):
                m = re.match(r'\[(\d+)\](.*)', part)
                if m:
                    idx = int(m.group(1))
                    current = current[idx]
                    part = m.group(2)
                else:
                    break
            # When at the last part, perform the update.
            if i == len(parts) - 1:
                if part:
                    # If part contains an index like key[index]
                    m = re.match(r'([^\[]+)(\[(\d+)\])?', part)
                    if m:
                        key = m.group(1)
                        if m.group(2):
                            idx = int(m.group(3))
                            current[key][idx] = value
                        else:
                            current[key] = value
                else:
                    # If no part remains, update current directly.
                    current = value
            else:
                if part:
                    m = re.match(r'([^\[]+)(\[(\d+)\])?', part)
                    if m:
                        key = m.group(1)
                        current = current[key]
                        if m.group(2):
                            idx = int(m.group(3))
                            current = current[idx]
                else:
                    continue
        return new_data

    def _update_workflow_from_leaves(self, workflow: Any, leaf_paths: list, new_values: list) -> Any:
        """
        Update the workflow based on a list of leaf paths,
        and a list of new values. For each leaf path, if the corresponding decision is True, the leaf's value
        in the workflow is replaced with the new value.
        """
        for path, new_value in zip(leaf_paths, new_values):
            workflow = self._set_by_path(workflow, path, new_value)
        return workflow

    def _classify_value(self, value: str) -> str:
        """
        Classify the input value as either 'reference' or 'literal' based on regex.
        If the value contains 'source:' or '.output.', it is classified as a reference.
        Otherwise, it is a literal.
        """
        # Pattern matches if "source:" or ".output." appears anywhere in the string.
        if (value is not None) and (re.search(r"(source:|\.output\.)", value)):
            return "reference"
        return "literal"

    def fix_literal_values(self, planned_workflow : dict, adapted_workflow : dict):

        """
        Replaces inputs that suppose to be literal in llm adapted workflow
        based on planned workflow.
        """

        og_leaves = self._extract_leaf_paths(planned_workflow)
        mod_leaves = self._extract_leaf_paths(adapted_workflow)

        self.logger.debug(f"og_leaves : {og_leaves}")
        self.logger.debug(f"mod_leaves : {mod_leaves}")


        ic_results = [self._classify_value(value) for value in og_leaves.values()]

        self.logger.debug(f"ic_results : {ic_results}")

        new_values = [mod_leaves[[olk for olk in list(mod_leaves.keys()) \
            if inputstr in olk][0]] if cl == 'reference' else og_leaves[inputstr] \
                for inputstr, cl in zip(og_leaves, ic_results)]

        leaf_paths = list(og_leaves.keys())

        cor_workflow = self._update_workflow_from_leaves(adapted_workflow, leaf_paths, new_values)

        return cor_workflow

    