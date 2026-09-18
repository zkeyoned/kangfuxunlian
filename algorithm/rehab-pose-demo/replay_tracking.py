"""Compare postprocessing on saved raw_metrics, without re-inferring annotated video.

Only selected-side points were saved by v0.2, so bilateral checks cannot replay.
This validates tracking behaviour, not anatomical keypoint accuracy.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

from rehab_pose.core import Analyzer,Config
from rehab_pose.tracking import PoseTracker,StrictPoseTracker,TrackingConfig


def replay(source,output):
    saved=json.loads((source/'summary.json').read_text(encoding='utf-8'))
    records=[json.loads(line) for line in (source/'frames.jsonl').read_text(encoding='utf-8').splitlines()]
    config=Config(**saved['effective_parameters'])
    tracking=TrackingConfig(**saved.get('tracking_parameters',{}))
    side=saved['side']; ids=(11,23,25,27) if side=='left' else (12,24,26,28)
    output.mkdir(parents=True,exist_ok=False)
    report={'input':str(source),'note':'Selected-side raw keypoint replay; no bilateral evidence; not accuracy validation','runs':{}}
    for name,cls in [('strict_v02',StrictPoseTracker),('short_gap_v03',PoseTracker)]:
        tracker=cls(side,config.min_confidence,tracking);analyzer=Analyzer(config)
        flags=Counter();observed=predicted=0
        with (output/(name+'.jsonl')).open('w',encoding='utf-8') as stream:
            for record in records:
                width=record['frame_size']['width'];height=record['frame_size']['height']
                raw=record['raw_metrics']['keypoints']
                landmarks=[]
                if raw:
                    landmarks=[dict(x=0.,y=0.,visibility=0.,presence=0.) for _ in range(33)]
                    for label,idx in zip(('shoulder','hip','knee','ankle'),ids):
                        p=raw[label]
                        landmarks[idx]=dict(x=p['x']/width if p['x'] is not None else float('nan'),
                                            y=p['y']/height if p['y'] is not None else float('nan'),
                                            visibility=p['confidence'],presence=p['confidence'])
                t=record['timestamp_s']
                m,q=tracker.update(t,landmarks,width,height)
                state=analyzer.update(t,m['value'],m['visible'],q.get('bridge_pending',False))
                observed+=int(m['visible']);predicted+=int(q.get('bridge_pending',False));flags.update(q['quality_flags'])
                stream.write(json.dumps(dict(**m,**state,**q),allow_nan=False)+'\n')
        analyzer.finish()
        report['runs'][name]=dict(frames=len(records),observed_frames=observed,prediction_frames=predicted,
                                 completed_reps=len(analyzer.reps),repetitions=analyzer.reps,
                                 interrupted_attempts=analyzer.interrupted,quality_flags=dict(flags))
    (output/'comparison.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    for name,data in report['runs'].items():
        print(name,{k:data[k] for k in ['frames','observed_frames','prediction_frames','completed_reps']})
        print('interruptions',len(data['interrupted_attempts']),'flags',data['quality_flags'])


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args();replay(args.source,args.output)
