"""Map internal measurements to the repository's stable algorithm contract."""


def rep_to_contract(rep, feedback_events=()):
    """Return the flat rep shape required by docs/03 A.

    Internal v0.1 measurements remain available in ``summary.repetitions``.
    This adapter keeps the front-end/backend boundary stable while those richer
    fields are reviewed by the team.
    """
    comparison=rep.get('target_comparison',{})
    flags=[]
    if comparison.get('amplitude_met') is False:flags.append('amplitude_low')
    too_fast=(comparison.get('extension_time_met') is False or
              comparison.get('return_time_met') is False)
    if too_fast:flags.append('too_fast')
    start,end=rep.get('start_s',0),rep.get('end_s',0)
    codes={e.get('code') for e in feedback_events
           if start<=e.get('timestamp_s',-1)<=end}
    if codes & {'TRUNK_FORWARD','TRUNK_BACKWARD'}:flags.append('trunk_lean')
    if 'THIGH_MOVEMENT' in codes:flags.append('hip_shift')
    return {'rep_index':rep['index'],
            'peak_angle':rep.get('knee_peak_deg',rep.get('max_included_deg')),
            'duration_ms':round(max(0,end-start)*1000),
            'valid':comparison.get('amplitude_met') is True and not too_fast,
            'flags':flags}
