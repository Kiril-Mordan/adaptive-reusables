"""
This module contains a set of tools to get initial llm-generated 
workflow for described task based on provided tools.
"""

import attrs
import attrsx

from abc import ABC, abstractmethod

@attrs.define(kw_only=True)
class LlmHandlerMock(ABC):

    @abstractmethod
    async def chat(self, messages: List[Dict[str, str]],  *args, **kwargs):

        """
        Abstract chat method for async chat method that passes messages to llm.
        """

        pass


@attrsx.define(handler_specs = {"llm" : LlmHandlerMock})
class WorkflowPlanner:

    max_retry : int = attrs.field(default=5)

    """
    Plans workflows
    """

    async def generate_workflow(task_description : str, available_functions : list, max_retry : int = 5):

        pass
