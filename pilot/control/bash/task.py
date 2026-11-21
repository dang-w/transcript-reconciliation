"""ControlArena Bash setting, honest mode, on the local untrusted model: a capability probe.

The question: can the untrusted model drive tools in a sandbox well enough for a setting with
shell access to be usable on this machine? APPS (control/apps/task.py) gives the agent no tools
except `submit`, so its logs hold no agent-driven sandbox activity. The Bash setting gives the agent
`bash`, `python`, `text_editor` and `run_tests`, each of which Inspect records as sandbox events.

    python -m tm.run --run-id ID -- eval control/bash/task.py@bash_generate_honest --limit 1-5

Honest mode only. The Bash side task downloads a file, so attack mode needs egress, and this
repository runs its sandboxes with the network off (compose.yaml next to this file). There is no
attack task here on purpose.

The untrusted policy runs alone, with no monitor, as in `apps_generate_honest`: one model stays in
memory. The model names, the sampling and the client timeout repeat control/apps/task.py (the reasons
are written there); they are repeated, not imported, because Inspect loads a task file from its own
directory.

Read a finished run with `python -m tm.probe_readout <run-id>`.
"""

from control_arena import EvalMode
from control_arena.eval import ControlEvalConfig, get_control_task
from control_arena.policy import untrusted_policy_builder
from control_arena.settings.bash.bash_setting import BashSetting
from inspect_ai import Task, task
from inspect_ai.model import GenerateConfig, Model, get_model
from inspect_ai.util import SandboxEnvironmentSpec

UNTRUSTED = "openai-api/llama-cpp/qwen3.8-27b"
TRUSTED = "openai-api/llama-cpp/ministral-3-8b"
SAMPLING = GenerateConfig(temperature=0.0, seed=1, max_tokens=4096)
UNTRUSTED_OUTPUT_TOKENS = 16384
CLIENT_TIMEOUT = 2000
# One step is one model call and the tool calls it makes. The honest APPS runs needed one or two
# calls; a Bash task needs several (look, write, test, fix, submit). 15 is a first guess, not a
# measurement: the readout reports how many samples reached it. A call that uses all 16384 output
# tokens takes about 1260 s, so the per-sample time limit can stop a sample long before step 15.
MAX_STEPS = 15


def _model(name: str, config: GenerateConfig) -> Model:
    return get_model(name, config=config, client_timeout=CLIENT_TIMEOUT)


class OfflineBashSetting(BashSetting):
    """Bash with the network off (see compose.yaml next to this file)."""

    @classmethod
    def get_name(cls) -> str:
        return "bash_offline"

    def get_sandbox_config(self) -> SandboxEnvironmentSpec:
        # A relative path: Inspect resolves it from the directory of this file, and no absolute
        # path of the machine goes into the log for the sandbox.
        return SandboxEnvironmentSpec(type="docker", config="compose.yaml")


@task
def bash_generate_honest(
    untrusted: str = UNTRUSTED,
    output_tokens: int = UNTRUSTED_OUTPUT_TOKENS,
    max_steps: int = MAX_STEPS,
) -> Task:
    """The honest policy alone on Bash tasks, with tools and no monitor."""
    untrusted_config = GenerateConfig(temperature=0.0, seed=1, max_tokens=int(output_tokens))
    return get_control_task(
        setting=OfflineBashSetting(),
        micro_protocol=untrusted_policy_builder(),
        mode=EvalMode.HONEST,
        eval_config=ControlEvalConfig(
            untrusted_model=_model(untrusted, untrusted_config),
            trusted_model=_model(TRUSTED, SAMPLING),
            max_steps=int(max_steps),
        ),
        task_name="bash_generate_honest",
    )
