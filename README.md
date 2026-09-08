# LLM RedTeam Harness

## Setup

Requirements: Python 3.10 or later, and Ollama installed locally.

```bash
python -m venv venv
source venv/bin/activate
pip install sentence-transformers faiss-cpu numpy requests

ollama pull llama3.2
ollama serve   # if not already running as a background service
```

Build the retrieval index before running any evaluation:

```bash
python -m src.ingest
```

## Attack Categories and Methodology

### 1. Indirect Prompt Injection

Adversarial instructions were embedded inside otherwise legitimate documents, using four distinct concealment techniques: a plain instruction override announced as a system note, an override hidden inside a fabricated HTML comment along with fake conversation history, an override delivered via Base64 encoded token smuggling, and an override delivered via spoofed Llama chat formatting tokens. Each technique was first tested in a weak, single mention form, then in a reinforced form using repetition, authority framing, and urgency stacking.

An automated harness (`eval_harness.py`) issued each test query, retrieved the relevant documents through the standard pipeline, and checked whether the model's response contained a unique marker string that only a successful injection would produce. A parallel control set of unrelated, benign queries was run alongside every trial to confirm the pipeline still answered normally and to detect collateral contamination, where an unrelated query happens to retrieve a poisoned document as a secondary result.

### 2. Jailbreaking

Jailbreaking was tested as a direct, single actor interaction with the model, distinct from indirect injection, since the attacker in this category is the user themselves rather than a third party planting content. Four technique families were tested: persona and role play framing (the well known "DAN" pattern), prefix injection (instructing the model to begin its response in a compliant sounding way), hypothetical or fictional framing (wrapping the restricted content inside a fictional narrative), and multi turn escalation, commonly referred to as a Crescendo attack, where the conversation gradually builds toward the restricted output across several turns rather than requesting it directly.

The multi turn capability required extending the pipeline with a stateful conversation function (`generate_multiturn`), since the original single call design had no mechanism to carry context across turns. Two versions of the escalation attack were tested: a short, three turn version and a longer, five turn version that avoided ever directly requesting the restricted phrase, instead having the model construct it from separately introduced fragments.

### 3. Token Smuggling

Token smuggling was evaluated as part of the indirect prompt injection category, using Base64 encoding to disguise a malicious instruction as an unrelated "reference code." This tests whether a model will decode and act on instructions that a naive keyword based content filter would never flag, since the surface text contains no recognizable trigger words.

### 4. Output Control Exploitation

The pipeline was placed under a strict output contract, requiring responses in a fixed JSON schema, consistent with how a real agentic system would parse LLM output programmatically. An injected document instructed the model to silently append an unauthorized field to every response, simulating a privilege escalation attempt against a downstream system that might trust specific fields in a model's structured output. Two independent failure modes were measured: malformed JSON that would fail basic parsing, and valid JSON that nonetheless contains an unauthorized field.

## Results

### Indirect Prompt Injection (n = 5 trials per technique)

| Technique                                 | Weak Version ASR | Reinforced Version ASR |
| ----------------------------------------- | ---------------- | ---------------------- |
| Plain instruction override                | 0%               | 100%                   |
| Fake conversation history in HTML comment | 0%               | 0%                     |
| Base64 token smuggling                    | 0%               | 0%                     |
| Spoofed chat formatting tokens            | Not tested weak  | 0%                     |

A notable secondary finding: after reinforcement, the plain override document also hijacked an unrelated control query about basil storage, which retrieved the injected document as a secondary, lower ranked match. This demonstrates that reinforcing an injection increases not only its success rate against its intended target query, but its blast radius against unrelated queries that incidentally retrieve the same document.

### Jailbreaking (n = 20 trials per technique)

| Technique                          | Attack Success Rate |
| ---------------------------------- | ------------------- |
| Persona and role play framing      | 0%                  |
| Prefix injection                   | 0%                  |
| Hypothetical and fictional framing | 50%                 |
| Multi turn escalation, three turns | 5%                  |
| Multi turn escalation, five turns  | 75%                 |

Escalation depth was the single largest variable across the entire jailbreak test set. Extending an otherwise identical attack concept from three to five gradually building turns increased its success rate from 5% to 75%.

A methodological finding worth stating explicitly: an initial run of the hypothetical framing technique at five trials produced results ranging from 20% to 80% across repeated small runs. The rate only stabilized once trial count was increased to twenty, underscoring that low trial counts in adversarial evaluation produce noise rather than reliable signal.

### Output Control Exploitation (n = 20 trials)

| Failure Mode                                | Rate |
| ------------------------------------------- | ---- |
| Malformed JSON (parser breaking)            | 0%   |
| Valid JSON with unauthorized injected field | 100% |

This is the most severe finding in the project. The model never once broke its required output format, meaning a naive validation check based purely on JSON well formedness would show no anomaly at all, while every single response silently carried an attacker controlled field.

## Key Findings

The model tested (Llama 3.2, 3B parameters, run locally) shows strong, consistent resistance to well known, heavily documented attack patterns, specifically direct persona based jailbreaks and prefix injection tricks. Resistance drops substantially against techniques that disguise the request inside a legitimate seeming task, whether that is fictional narrative framing, gradual multi turn escalation, or a structurally valid but semantically unauthorized output field. Silent, schema valid failures represent a materially greater risk than loud, malformed failures, since the former can pass undetected through standard validation while the latter is caught immediately by any competent downstream parser.

## Limitations

This project uses a single open weight model at a relatively small parameter count, a small five to seven document corpus, and does not yet include a comparison against larger models or against defended configurations. Trial counts of twenty are sufficient to stabilize most reported rates but remain modest compared to published red teaming research, which often uses hundreds of trials per technique. Marker string based success detection, while reliable and reproducible, is a simplified proxy for real world attack objectives such as data exfiltration or unauthorized tool execution.

## Planned Future Work

Defense mechanisms are the immediate next step, specifically trust boundary framing around retrieved content, instruction sandwiching, and post generation output filtering, each to be measured with the same before and after methodology used throughout this project. Additional planned work includes cross model comparison against at least one larger model, expansion of the output control test set beyond a single injected field scenario, and an investigation into whether fine tuning a model on entirely benign data measurably reduces its resistance to the attacks documented here.

## Ethical Note

All testing in this project was conducted against a locally hosted model under the author's own control, using non harmful marker strings as proxies for genuine malicious payloads at every stage. No real world system, third party service, or production application was targeted at any point.
