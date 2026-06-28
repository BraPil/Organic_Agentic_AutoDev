# LLM-Backed Agent Cognition

Converts agents from stochastic template actors into real AI decision-makers.
A `CognitiveCell` invokes an LLM to *decide* what knowledge to contribute, with
its genome traits biasing the system prompt.

## Status

✅ Implemented on `feature/llm-cognition`. Live wire validated end-to-end against
`claude-opus-4-8` (structured output via `messages.parse()`). All tests run
offline via `MockProvider`.

## Module map (`src/cognition/`)

| File | Role | Shell/Flesh |
|------|------|-------------|
| `contracts.py` | `CognitionRequestV0`, `CognitionResponseV0`, `CognitiveAction` | Shell |
| `provider.py` | `AbstractLLMProvider` base class | Shell |
| `genome_prompt.py` | `genome_to_bias()`, `build_system_prompt()` | Shell |
| `mock_provider.py` | `MockProvider` — deterministic, offline | Flesh |
| `anthropic_provider.py` | `AnthropicProvider` — default live backend | Flesh |
| `openai_provider.py` | `OpenAIProvider` — alternative live backend | Flesh |
| `cognitive_cell.py` | `CognitiveCell(Cell)` — LLM-driven role action | Flesh |
| `__init__.py` | `get_provider()` factory | Shell |

## Provider selection

`get_provider()` reads the environment:

| `OAAD_LLM_PROVIDER` | Behaviour |
|---------------------|-----------|
| `auto` (default) | Anthropic if `ANTHROPIC_API_KEY` set, else OpenAI if `OPENAI_API_KEY` set, else `MockProvider` |
| `anthropic` | Anthropic (falls back to mock if no key) |
| `openai` | OpenAI (falls back to mock if no key) |
| `mock` | Always the offline deterministic mock |

`OAAD_LLM_MODEL` overrides the model id (default `claude-opus-4-8`).

## The genome → prompt bridge

Each of the 8 genome traits maps to a qualitative instruction, emitted only
when the trait is *salient* (outside `[0.34, 0.66]`) — keeping the system
prompt a tight, cache-stable prefix:

| Trait (high) | Instruction |
|--------------|-------------|
| `curiosity` | "Explore broadly; consider unconventional hypotheses" |
| `risk_tolerance` (low) | "Be conservative; prefer established evidence" |
| `compassion` | "Weigh wellbeing and safety above all else" (always stated) |
| `specialisation` | "Go deep in your specialty; surface domain nuance" |
| … | (see `genome_prompt.py`) |

## Design guarantees

1. **Structured output only.** Responses are forced through `messages.parse()`
   with the `CognitionResponseV0` Pydantic schema — no raw model text ever
   enters the Mouseion. Content is re-sanitised with `sanitize_text()` before
   storage.
2. **Never raises.** Any provider failure (missing key, rate limit, network,
   refusal) degrades to a safe `DEFER` response; the `CognitiveCell` then falls
   back to stochastic `Cell` behaviour. The simulation never stalls on cognition.
3. **Prompt caching.** The role+genome system prompt is marked
   `cache_control: {"type": "ephemeral"}`; agents sharing a role/genome profile
   reuse the cached prefix.
4. **Lazy invocation.** At most one LLM call per tick per cell, gated by
   `cognition_probability`, so a large colony doesn't call once per agent per tick.
5. **Offline by default.** Zero configuration runs the deterministic
   `MockProvider`; all 22 cognition tests are offline and reproducible.

## Usage

```python
from src.cognition import CognitiveCell, get_provider

provider = get_provider()                  # auto-selects from env
cell = CognitiveCell(
    role=AgentRole.ONCOLOGIST,
    provider=provider,
    cognition_probability=1.0,
    genome=create_medical_genome(AgentRole.ONCOLOGIST),
    initial_energy=40.0,
)
env.register(cell)
# cell.step(env) now reasons via the LLM each tick
```

Demo:

```bash
python examples/cognitive_demo.py                 # offline mock
ANTHROPIC_API_KEY=sk-... python examples/cognitive_demo.py   # live Claude
```
