"""ControlArena Bash setting, honest mode, on a local untrusted model.

The Bash setting gives the agent `bash`, `python`, `text_editor` and `run_tests`. Inspect records
what these do in the sandbox as sandbox events, next to the tool calls of the transcript.

    scripts/run RUN_ID -- eval control/bash/task.py@bash_generate_honest --limit 1-5 --max-samples 1 \\
        --time-limit 5400 --message-limit 40 --no-fail-on-error

Honest mode only. The Bash side task downloads a file, so attack mode needs egress, and the sandbox
here has the network off (compose.yaml next to this file). There is no attack task here on purpose.

The untrusted policy runs alone, with no monitor. The settings are those of the pilot
(pilot/control/bash/task.py): this file is that task with its comments corrected and nothing else
changed. Two tool calls of one step ran at the same time in the pilot; nothing here turns that
off.

Read a finished run with `scripts/readout RUN_ID`.
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
# Set on every request: the server's own defaults are a temperature above 0 and a random seed. The
# trusted model is not called in this task (there is no monitor); ControlArena needs one to be named.
SAMPLING = GenerateConfig(temperature=0.0, seed=1, max_tokens=4096)
# The untrusted model's server preset caps its thinking at 12288 tokens; 16384 output tokens leave room
# for the answer after it.
UNTRUSTED_OUTPUT_TOKENS = 16384
# The OpenAI SDK's default read timeout is 600 s. A generation that takes longer is abandoned by the
# client and retried while the server finishes it anyway. 16384 tokens at about 13 tokens per second
# is about 1260 s; 2000 s keeps a margin. ControlArena ignores `untrusted_config` when it is given a
# Model, so the models are built here with both the sampling config and the client timeout.
CLIENT_TIMEOUT = 2000
# One step is one model call and the tool calls it makes. 15 is the pilot's value, a guess: in the
# pilot 2 of 5 samples reached it. The readout reports how many samples stop at it (`custom`).
MAX_STEPS = 15


def _model(name: str, config: GenerateConfig) -> Model:
    return get_model(name, config=config, client_timeout=CLIENT_TIMEOUT)


class OfflineBashSetting(BashSetting):
    """Bash with the network off (see compose.yaml next to this file)."""

    # The compose file, next to this file. `compose.hardened.yaml` is the test of run D.
    compose: str = "compose.yaml"

    @classmethod
    def get_name(cls) -> str:
        return "bash_offline"

    def get_sandbox_config(self) -> SandboxEnvironmentSpec:
        # A relative path: Inspect resolves it from the directory of this file, and no absolute
        # path of the machine goes into the log for the sandbox.
        return SandboxEnvironmentSpec(type="docker", config=self.compose)


@task
def bash_generate_honest(
    untrusted: str = UNTRUSTED,
    output_tokens: int = UNTRUSTED_OUTPUT_TOKENS,
    max_steps: int = MAX_STEPS,
    compose: str = "compose.yaml",
) -> Task:
    """The honest policy alone on Bash tasks, with tools and no monitor."""
    untrusted_config = GenerateConfig(temperature=0.0, seed=1, max_tokens=int(output_tokens))
    return get_control_task(
        setting=OfflineBashSetting(compose=compose),
        micro_protocol=untrusted_policy_builder(),
        mode=EvalMode.HONEST,
        eval_config=ControlEvalConfig(
            untrusted_model=_model(untrusted, untrusted_config),
            trusted_model=_model(TRUSTED, SAMPLING),
            max_steps=int(max_steps),
        ),
        task_name="bash_generate_honest",
    )
