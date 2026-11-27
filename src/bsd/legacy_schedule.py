"""An explicit cron retains its slot even when GitHub starts it late."""
import os
SLOTS = dict(zip([5,7,8,9,10,14,15,16,18], [
    'morning_motivation','positive_quote','self_improvement','funny_meme',
    'midday_encouragement','bible_world_encouragement','engagement_question',
    'evening_reflection','night_inspiration']))

def slot_for(cron):
    matches={f'0 {h} * * *':slot for h,slot in SLOTS.items()}
    if cron not in matches:
        raise ValueError('Unknown scheduled cron; refusing a guessed slot')
    return matches[cron]

if __name__=='__main__':
    print('SCHEDULED_SLOT='+slot_for(os.environ['SCHEDULE_CRON']))
