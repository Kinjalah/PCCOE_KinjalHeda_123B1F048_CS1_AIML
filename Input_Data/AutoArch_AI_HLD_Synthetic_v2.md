# Synthetic AUTOSAR style HLD

## 1 Purpose and boundary
This is a synthetic AUTOSAR-style HLD for a classroom steering monitoring example. It is not an AUTOSAR standard, production ECU design or safety-certified system.
Document: SYN-HLD-001 | Version: v2 | Status: Learning example
Scope: component interfaces, declared signals, ports, timing and engineer review. No ASIL rating is assigned.
The example reads vehicle speed, computes steering control state and monitors steering angle. Outputs are design-review evidence only.

## 2 Component catalogue
Component: VehicleStateProvider | Role: publishes vehicle speed | Owner: VehicleInputs | RateMs: 10
Component: SteeringController | Role: consumes vehicle speed and publishes steering angle | Owner: SteeringControl | RateMs: 10
Component: SafetyMonitor | Role: consumes steering angle and checks range | Owner: Monitoring | RateMs: 10
Component: DiagnosticManager | Role: consumes fault status for diagnostic review | Owner: Diagnostics | RateMs: 50

## 3 Interface catalogue
Interface: VehicleSpeedIf | Direction: sender-receiver | DataElement: VehicleSpeed | Type: float32
Interface: SteeringAngleIf | Direction: sender-receiver | DataElement: SteeringAngle | Type: float32
Interface: DiagnosticStatusIf | Direction: sender-receiver | DataElement: FaultStatus | Type: uint8

## 4 Signal contracts
Signal: VehicleSpeed | Producer: VehicleStateProvider | Consumer: SteeringController | Interface: VehicleSpeedIf | Type: float32 | ProducerUnit: km_per_h | ConsumerUnit: km_per_h | PeriodMs: 10
Signal: SteeringAngle | Producer: SteeringController | Consumer: SafetyMonitor | Interface: SteeringAngleIf | Type: float32 | ProducerUnit: rad | ConsumerUnit: deg | PeriodMs: 10
Signal: FaultStatus | Producer: SafetyMonitor | Consumer: DiagnosticManager | Interface: DiagnosticStatusIf | Type: uint8 | ProducerUnit: status_code | ConsumerUnit: status_code | PeriodMs: 50

## 5 Port mapping
Port: SpeedOut | Component: VehicleStateProvider | Direction: provided | Interface: VehicleSpeedIf
Port: SpeedIn | Component: SteeringController | Direction: required | Interface: VehicleSpeedIf
Port: AngleOut | Component: SteeringController | Direction: provided | Interface: SteeringAngleIf
Port: AngleIn | Component: SafetyMonitor | Direction: required | Interface: SteeringAngleIf
Port: FaultOut | Component: SafetyMonitor | Direction: provided | Interface: DiagnosticStatusIf
Port: FaultIn | Component: DiagnosticManager | Direction: required | Interface: DiagnosticStatusIf

## 6 Review and limitations
Engineer review is mandatory before accepting any generated answer, extraction, revision finding or impact result.
No ASIL classification, hazard analysis, AUTOSAR conformance validation or production safety decision is defined in this HLD.
Model output must cite the document ID, version, page and section. Unsupported factual requests must be refused.
All names, interfaces and numeric values in this HLD were generated for the educational prototype.

## 7 Functional requirements
Requirement: REQ-001 | Text: VehicleStateProvider shall publish VehicleSpeed every 10 ms.
Requirement: REQ-002 | Text: SteeringController shall consume VehicleSpeed through VehicleSpeedIf.
Requirement: REQ-003 | Text: SafetyMonitor shall consume SteeringAngle through SteeringAngleIf.
Requirement: REQ-004 | Text: Engineer review shall be recorded separately before architecture approval.
Requirement: REQ-005 | Text: DiagnosticManager shall consume FaultStatus every 50 ms.
Known review seed: SteeringAngle has producer unit rad and consumer unit deg; this intentional inconsistency tests the unit-mismatch rule.
