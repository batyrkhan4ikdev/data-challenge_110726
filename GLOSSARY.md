# Conversation Quality Analytics

Scoring of contact-center operators' chats and calls against a configurable checklist, with appeals and reviewer decisions.

## Language

### Data

**Dialog**:
One customer conversation (an agent chat or a voice call) identified by `conversation_id`.
_Avoid_: conversation record, case

**Turn**:
One line of a dialog's transcript, addressed by its position `idx`.
_Avoid_: message, replica, utterance

**Group**:
A dataset batch fetched by `group_id` (`DEV`, or the control group given at +23h).
_Avoid_: dataset id, set

### Checklist

**Checklist**:
A named, versioned set of criteria with weights, used to score dialogs of a default channel.
_Avoid_: rubric, template

**Criterion**:
One question about operator behaviour in a checklist, answered yes/no or by a scale step.
_Avoid_: item, question, metric

**Verdict**:
The answer to one criterion: `yes`, `no`, `na`, or a scale step value.
_Avoid_: answer, grade, label

**Gross error**:
A criterion that carries no points and flags an insult, an offer of service outside the company, or disclosure of confidential data.
_Avoid_: critical error, fatal

### Scoring

**Evaluation**:
An immutable record of one dialog scored under one checklist version, holding the verdicts, evidence, score, and the raw model calls behind them.
_Avoid_: assessment, result, run

**Evidence**:
The turns a verdict rests on; for a missed action, the range of turns where it was expected.
_Avoid_: proof, citation

**Total**:
Weighted score out of 100 after redistributing the weight of N/A criteria; absent when no weighted criterion applies.
_Avoid_: grade, final score

**Appeal**:
A dispute of one criterion's verdict in an evaluation, with a comment.
_Avoid_: complaint, dispute

**Decision**:
A reviewer's confirm-or-change ruling on an appeal, with a reason.
_Avoid_: resolution, review

**Final result**:
The evaluation's verdicts with accepted decisions applied, and the recomputed total.
_Avoid_: corrected score

### Accuracy

**Gold**:
Human-corrected verdicts for the labeled DEV dialogs, used as our stand-in for the organizers' Ground Truth.
_Avoid_: ground truth (reserved for the organizers' hidden reference), labels

**Profile**:
A named model configuration: endpoint, model, cost model.
_Avoid_: provider, backend
