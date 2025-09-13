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

    def _set_by_path(self, data: Any, path: str, value: Any) -> Any:
        """
        Return a modified copy of a nested structure (dicts/lists) given a path string.
        
        Path format uses:
        - dots for nested dict keys (e.g. "args.info")
        - [index] for list indices (e.g. "[2].args.information[1].content")
        """
        new_data = copy.deepcopy(data)
        parts = re.split(r'\.(?![^\[]*\])', path)  # split on dots not inside [ ]

        current = new_data
        parents = []   # keep track of parent containers + keys/indices

        for i, part in enumerate(parts):
            # --- Handle list indices that start the part ---
            while part.startswith('['):
                m = re.match(r'\[(\d+)\](.*)', part)
                if not m:
                    break
                idx, rest = int(m.group(1)), m.group(2)
                if not isinstance(current, list) or idx >= len(current):
                    return new_data  # invalid path → return unchanged
                parents.append((current, idx))
                current = current[idx]
                part = rest

            # --- If this is the last part → assign the value ---
            if i == len(parts) - 1:
                if part:  # dict key, maybe with list index
                    m = re.match(r'([^\[]+)(\[(\d+)\])?', part)
                    if not m:
                        return new_data
                    key = m.group(1)

                    if isinstance(current, dict):
                        if key not in current:
                            return new_data
                        if m.group(2):  # key[index]
                            idx = int(m.group(3))
                            if not isinstance(current[key], list) or idx >= len(current[key]):
                                return new_data
                            current[key][idx] = value
                        else:
                            current[key] = value
                    elif isinstance(current, list):
                        try:
                            idx = int(key)
                            if idx >= len(current):
                                return new_data
                            current[idx] = value
                        except ValueError:
                            return new_data
                else:
                    # No part left → replace the entire object
                    # e.g. path = "[0]" and we reached the end
                    parent, idx_or_key = parents[-1]
                    parent[idx_or_key] = value
            else:
                # --- Traverse deeper ---
                if part:
                    m = re.match(r'([^\[]+)(\[(\d+)\])?', part)
                    if not m:
                        return new_data
                    key = m.group(1)

                    if isinstance(current, dict):
                        if key not in current:
                            return new_data
                        current = current[key]
                        if m.group(2):  # key[index]
                            idx = int(m.group(3))
                            if not isinstance(current, list) or idx >= len(current):
                                return new_data
                            parents.append((current, idx))
                            current = current[idx]
                    elif isinstance(current, list):
                        try:
                            idx = int(key)
                            current = current[idx]
                        except (ValueError, IndexError):
                            return new_data
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
            if new_value:
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

    def _get_new_leaf_with_old_key(self, mod_leaves, inputstr):

        new_vals = [olk for olk in list(mod_leaves.keys()) if inputstr in olk]
        new_val = ""
        if new_vals:
            new_val = new_vals[0]

        return new_val

    def fix_literal_values(self, planned_workflow : dict, adapted_workflow : dict):

        """
        Replaces inputs that suppose to be literal in llm adapted workflow
        based on planned workflow.
        """

        og_leaves = self._extract_leaf_paths(planned_workflow)
        for k,v in og_leaves.items():
            if v is not None:
                v = str(v)
            og_leaves[k] = v

        mod_leaves = self._extract_leaf_paths(adapted_workflow)
        for k,v in mod_leaves.items():
            if v is not None:
                v = str(v)
            mod_leaves[k] = v

        self.logger.debug(f"og_leaves : {og_leaves}")
        self.logger.debug(f"mod_leaves : {mod_leaves}")


        ic_results = [self._classify_value(value) for value in og_leaves.values()]

        self.logger.debug(f"ic_results : {ic_results}")

        new_values = [mod_leaves.get(self._get_new_leaf_with_old_key(
            mod_leaves = mod_leaves, inputstr = inputstr), None) if cl == 'reference' else og_leaves[inputstr] \
                for inputstr, cl, mv in zip(og_leaves, ic_results, mod_leaves)]

        self.logger.debug(f"new_values : {new_values}")

        if len(mod_leaves) > len(og_leaves):
            new_values += [None for _ in range(len(mod_leaves) - len(og_leaves))]

        leaf_paths = list(og_leaves.keys())

        cor_workflow = self._update_workflow_from_leaves(adapted_workflow, leaf_paths, new_values)

        return cor_workflow

    