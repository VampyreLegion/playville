from dataclasses import dataclass, field
import time
import random


@dataclass
class Evidence:
    title: str
    description: str
    weight: int   # 1-10, prosecution strength


@dataclass
class CourtCase:
    defendant: str
    charge: str
    evidence: list  # List[Evidence]
    witnesses: list  # List[str] npc names
    jury: list       # List[str] npc names (everyone except defendant)
    phase: str = 'opening'   # opening|evidence|deliberation|verdict
    phase_timer: int = 0
    evidence_index: int = 0
    votes_guilty: int = 0
    votes_innocent: int = 0
    verdict: str = None      # 'guilty'|'innocent'
    started_at: float = field(default_factory=time.time)


class CourtCaseManager:
    def __init__(self):
        self.active_case: CourtCase = None
        self.case_history = []

    def file_case(self, defendant_name, charge, all_npcs):
        """Start a new court case. Generates evidence from NPC secrets/gossip."""
        # Build jury from all NPCs except defendant
        jury = [npc.name for npc in all_npcs if npc.name != defendant_name]
        witnesses = random.sample(jury, min(3, len(jury)))

        # Generate evidence based on available gossip/secrets
        defendant_npc = next((n for n in all_npcs if n.name == defendant_name), None)
        evidence_list = []

        # Generic evidence items
        evidence_list.append(Evidence(
            title="Witness Testimony",
            description=f"Multiple witnesses report suspicious behavior from {defendant_name}",
            weight=random.randint(3, 7)
        ))
        evidence_list.append(Evidence(
            title="Circumstantial Evidence",
            description=f"Timeline of events places {defendant_name} at the scene",
            weight=random.randint(2, 6)
        ))

        if defendant_npc and hasattr(defendant_npc, 'secrets') and defendant_npc.secrets:
            # Use first secret as evidence
            secret = defendant_npc.secrets[0] if defendant_npc.secrets else ""
            if secret:
                evidence_list.append(Evidence(
                    title="Character Evidence",
                    description=f"Records indicate: {secret[:80]}",
                    weight=random.randint(1, 8)
                ))

        self.active_case = CourtCase(
            defendant=defendant_name,
            charge=charge,
            evidence=evidence_list,
            witnesses=witnesses,
            jury=jury
        )

    def update(self, phase_durations):
        """Advance phase timer; returns ('phase_change', new_phase), ('vote_time', ...), ('case_over', ...) or None."""
        if not self.active_case:
            return None

        case = self.active_case
        case.phase_timer += 1

        if case.phase == 'opening':
            duration = phase_durations.get('opening', 300)
            if case.phase_timer >= duration:
                case.phase = 'evidence'
                case.phase_timer = 0
                return ('phase_change', 'evidence')

        elif case.phase == 'evidence':
            duration = phase_durations.get('evidence', 180)
            if case.phase_timer >= duration:
                case.evidence_index += 1
                case.phase_timer = 0
                if case.evidence_index >= len(case.evidence):
                    case.phase = 'deliberation'
                    return ('phase_change', 'deliberation')

        elif case.phase == 'deliberation':
            duration = phase_durations.get('deliberation', 600)
            if case.phase_timer == 1:
                return ('vote_time', None)
            if case.phase_timer >= duration:
                case.phase = 'verdict'
                case.phase_timer = 0
                self.finalize_verdict()
                return ('phase_change', 'verdict')

        elif case.phase == 'verdict':
            duration = phase_durations.get('verdict', 480)
            if case.phase_timer >= duration:
                self.case_history.append(self.active_case)
                self.active_case = None
                return ('case_over', None)

        return None

    def cast_vote(self, npc, evidence_list):
        """NPC votes based on personality + evidence weight."""
        if not self.active_case:
            return

        total_weight = sum(e.weight for e in evidence_list) if evidence_list else 0
        avg_weight = total_weight / len(evidence_list) if evidence_list else 0

        # Base probability of guilty vote from evidence weight (0-10 scale -> 0-1)
        guilty_prob = avg_weight / 10.0

        # Personality modifiers
        personality = getattr(npc, 'personality', [])
        if 'analytical' in personality:
            # Analytical NPCs lean on evidence more strictly
            guilty_prob = guilty_prob * 1.2
        if 'friendly' in personality:
            # Friendly NPCs give benefit of the doubt
            guilty_prob -= 0.1
        if 'paranoid' in personality or 'suspicious' in personality:
            guilty_prob += 0.15

        guilty_prob = max(0.05, min(0.95, guilty_prob))

        if random.random() < guilty_prob:
            self.active_case.votes_guilty += 1
        else:
            self.active_case.votes_innocent += 1

    def finalize_verdict(self):
        """Compare votes; set verdict; archive case."""
        if not self.active_case:
            return
        case = self.active_case
        total_votes = case.votes_guilty + case.votes_innocent
        if total_votes == 0:
            case.verdict = 'innocent'
        elif case.votes_guilty > case.votes_innocent:
            case.verdict = 'guilty'
        else:
            case.verdict = 'innocent'

    def get_display_lines(self, npcs_dict):
        """Return list of strings for court cutscene rendering."""
        if not self.active_case:
            return ["No active case"]

        case = self.active_case
        lines = []
        lines.append(f"CASE: {case.charge}")
        lines.append(f"Defendant: {case.defendant}")
        lines.append(f"Phase: {case.phase.upper()}")
        lines.append("")

        if case.phase == 'opening':
            lines.append("The court is now in session.")
            lines.append(f"The defendant, {case.defendant}, stands accused of:")
            lines.append(f"  {case.charge}")

        elif case.phase == 'evidence':
            if case.evidence_index < len(case.evidence):
                ev = case.evidence[case.evidence_index]
                lines.append(f"EVIDENCE #{case.evidence_index + 1}: {ev.title}")
                lines.append(f"  {ev.description}")
                lines.append(f"  (Prosecution strength: {ev.weight}/10)")
            lines.append(f"Progress: {case.evidence_index}/{len(case.evidence)} items presented")

        elif case.phase == 'deliberation':
            lines.append("The jury deliberates...")
            lines.append(f"Votes so far — Guilty: {case.votes_guilty}  Innocent: {case.votes_innocent}")

        elif case.phase == 'verdict':
            verdict_str = case.verdict.upper() if case.verdict else "PENDING"
            lines.append(f"VERDICT: {verdict_str}")
            lines.append(f"Final vote — Guilty: {case.votes_guilty}  Innocent: {case.votes_innocent}")
            if case.verdict == 'guilty':
                lines.append(f"{case.defendant} is found GUILTY!")
            else:
                lines.append(f"{case.defendant} is found INNOCENT!")

        return lines
