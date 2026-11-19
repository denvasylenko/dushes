# experimental-features Specification

## Purpose
Let a host keep an experimental feature off for everyone except a person who entered an activation code. The first such feature is the decision model (the choice layer): a visitor without a code sends nothing to the chooser's supplier.

## Requirements

### Requirement: A code opens the experimental features
A host that sets `EXPERIMENT_CODES` SHALL offer `GET /experiments` (the features a code opens here and whether this request holds a pass) and `POST /experiments/unlock`, which returns a signed pass for a right code and 403 for a wrong one. The codes SHALL be a list of their own, separate from the voice codes.

#### Scenario: A right code
- **WHEN** a person posts their code to `/experiments/unlock`
- **THEN** the answer holds their name, a pass and the list of features

#### Scenario: A wrong code
- **WHEN** a code that is on no list is posted
- **THEN** the answer is 403 and no pass is given

### Requirement: Without a pass the decision model is not asked
On a gated host the choice layer SHALL run only for a request that carries a valid pass in the `X-Experiment-Pass` header. For any other request the chooser SHALL NOT be called, and no label, score or decision trace SHALL be sent. A host with no gate SHALL behave as its own settings say.

#### Scenario: A visitor without a pass
- **WHEN** a visitor on a gated host writes "open the loans page" with no pass
- **THEN** nothing is sent to the chooser and the assistant answers as it does with the layer off

#### Scenario: A person with a pass
- **WHEN** the same line arrives with a valid pass
- **THEN** the layer may carry it out, and the label and the trace follow the host's switches

### Requirement: One code entry for every experimental feature
A host MAY join its other code-gated features (the voice mode) to the gate. `POST /experiments/unlock` SHALL then try the code against each feature's own list and answer with the features it opens and a pass for each (`passes`). A code that is only on another feature's list SHALL NOT give a pass for the decision model.

#### Scenario: A code on both lists
- **WHEN** a person whose code is on the voice list and on the experiments list enters it once
- **THEN** the answer holds a pass for voice and a pass for the decision model

#### Scenario: A code on the voice list only
- **WHEN** a person whose code is only on the voice list enters it
- **THEN** the answer holds a pass for voice only, and the decision model stays off for them

### Requirement: A host decides the decision model for each run
A host's server MAY say for one run of the site agent whether the choice layer may run (`layer`), add its own never-send items for that run (`never_send`), and send the chooser no earlier messages of the conversation (`layer_history`, or `INTENT_HISTORY=0` for the process). None of these is read from the client. The host's word for the run SHALL override the process settings and the experiments gate.

#### Scenario: Off for a visitor, on for the owner
- **WHEN** the host passes `layer=False` for a visitor's run and `layer=True` for the owner's
- **THEN** the chooser is asked only in the owner's run

#### Scenario: A guest's name
- **WHEN** the host passes a guest's name in `never_send` for a run
- **THEN** a line that holds the name is not sent to the chooser, and the name is masked in everything else that is

### Requirement: The chooser's call is in the run's numbers
When the chooser was asked in a run, the run's `run_stats` SHALL carry one entry of kind `chooser` in `models`, with its model, input tokens and cost, so a host that counts usage and money per run counts it too.

#### Scenario: A turn the layer handled alone
- **WHEN** the layer carries a line out with no model call
- **THEN** the run still ends with `run_stats`, whose only model entry is the chooser's
