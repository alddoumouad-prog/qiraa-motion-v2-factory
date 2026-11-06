#!/usr/bin/env python3
"""Validate and resolve an optional, bounded Motion V2 creative plan.

No facts or scripts are generated here. The editorial agent creates the plan,
checks evidence and chooses a style; auto is a transparent style heuristic only.
"""
from __future__ import annotations

MODES=('golden','auto','quote','scene','context')
HOOKS=('fact','question','quote','contrast','visual','explainer')
CROPS=('center','auto','left','right')
POSITIONS=('auto','upper','lower')
FIELDS={'mode','angle','reason','hook_type','crop','card_position'}

def validate(spec):
    if 'creative' not in spec:
        return {'requested_mode':'golden','mode':'golden','angle':None,'reason':None,
                'hook_type':None,'crop':'center','card_position':'lower','selection':'legacy_golden'}
    c=spec['creative']
    if not isinstance(c,dict):raise ValueError('creative must be an object')
    unknown=set(c)-FIELDS
    if unknown:raise ValueError('Unknown creative fields: '+', '.join(sorted(unknown)))
    mode=c.get('mode')
    if mode not in MODES:raise ValueError('creative.mode must be golden, auto, quote, scene or context')
    crop=c.get('crop','center' if mode=='golden' else 'auto')
    position=c.get('card_position','lower' if mode=='golden' else 'auto')
    if crop not in CROPS:raise ValueError('creative.crop must be center, auto, left or right')
    if position not in POSITIONS:raise ValueError('creative.card_position must be auto, upper or lower')
    angle=c.get('angle');reason=c.get('reason');hook=c.get('hook_type')
    if mode!='golden':
        if not isinstance(angle,str) or not 10<=len(angle.strip())<=240:raise ValueError('creative.angle must describe the verified story angle in 10–240 characters')
        if not isinstance(reason,str) or not 5<=len(reason.strip())<=300:raise ValueError('creative.reason must explain the profile choice in 5–300 characters')
        if hook not in HOOKS:raise ValueError('creative.hook_type must be fact, question, quote, contrast, visual or explainer')
    else:
        if angle is not None and (not isinstance(angle,str) or len(angle)>240):raise ValueError('Invalid creative.angle')
        if reason is not None and (not isinstance(reason,str) or len(reason)>300):raise ValueError('Invalid creative.reason')
        if hook is not None and hook not in HOOKS:raise ValueError('Invalid creative.hook_type')
    selected=mode;selection='agent_selected' if mode!='auto' else 'hook_type_heuristic'
    if mode=='auto':
        selected={'quote':'quote','visual':'scene','question':'context','explainer':'context','contrast':'context','fact':'scene'}[hook]
    return {'requested_mode':mode,'mode':selected,'angle':angle,'reason':reason,
            'hook_type':hook,'crop':crop,'card_position':position,'selection':selection}
