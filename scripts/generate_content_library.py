"""
Generate the full content library for Bright Side Daily.
Run once to populate all JSON content files.
"""
import json
import os
import random

# ─────────────────────────────────────────────
# RAW CONTENT SEEDS (expanded programmatically)
# ─────────────────────────────────────────────

MOTIVATIONAL_BASE = [
    "Success begins when excuses end.",
    "Push yourself because no one else will do it for you.",
    "Great things never come from comfort zones.",
    "Dream it. Wish it. Do it.",
    "Success doesn't just find you. You have to go out and get it.",
    "The harder you work for something, the greater you'll feel when you achieve it.",
    "Dream bigger. Do bigger.",
    "Don't stop when you're tired. Stop when you're done.",
    "Wake up with determination. Go to bed with satisfaction.",
    "Do something today that your future self will thank you for.",
    "Little things make big days.",
    "It's going to be hard, but hard is not impossible.",
    "Don't wait for opportunity. Create it.",
    "Sometimes we're tested not to show our weaknesses, but to discover our strengths.",
    "The key to success is to focus on goals, not obstacles.",
    "Dream it. Believe it. Build it.",
    "Don't limit your challenges. Challenge your limits.",
    "Energy and persistence conquer all things.",
    "Act as if what you do makes a difference. It does.",
    "Success is the sum of small efforts repeated day in and day out.",
    "Start where you are. Use what you have. Do what you can.",
    "It always seems impossible until it's done.",
    "You don't have to be great to start, but you have to start to be great.",
    "The secret of getting ahead is getting started.",
    "Keep going. Everything you need will come to you at the perfect time.",
    "Believe you can and you're halfway there.",
    "The only way to do great work is to love what you do.",
    "In the middle of every difficulty lies opportunity.",
    "It does not matter how slowly you go as long as you do not stop.",
    "Life is 10% what happens to you and 90% how you react to it.",
    "The best time to plant a tree was 20 years ago. The second best time is now.",
    "An unexamined life is not worth living.",
    "Spread love everywhere you go.",
    "When you reach the end of your rope, tie a knot in it and hang on.",
    "Always remember that you are absolutely unique.",
    "Don't judge each day by the harvest you reap but by the seeds that you plant.",
    "The future belongs to those who believe in the beauty of their dreams.",
    "Tell me and I forget. Teach me and I remember. Involve me and I learn.",
    "When one door of happiness closes, another opens.",
    "Do not go where the path may lead, go instead where there is no path and leave a trail.",
    "You will face many defeats in life, but never let yourself be defeated.",
    "The greatest glory in living lies not in never falling, but in rising every time we fall.",
    "In the end, it's not the years in your life that count. It's the life in your years.",
    "Never let the fear of striking out keep you from playing the game.",
    "Life is either a daring adventure or nothing at all.",
    "Many of life's failures are people who did not realize how close they were to success when they gave up.",
    "You have brains in your head. You have feet in your shoes. You can steer yourself any direction you choose.",
    "If life were predictable it would cease to be life and be without flavor.",
    "If you look at what you have in life, you'll always have more.",
    "If you set your goals ridiculously high and it's a failure, you will fail above everyone else's success.",
]

POSITIVE_LIFE_BASE = [
    "Every day may not be good, but there is something good in every day.",
    "Positive anything is better than negative nothing.",
    "Happiness is not something readymade. It comes from your own actions.",
    "Once you replace negative thoughts with positive ones, you'll start having positive results.",
    "Keep your face always toward the sunshine, and shadows will fall behind you.",
    "You are enough just as you are.",
    "Life is short. Smile while you still have teeth.",
    "Choose to be optimistic. It feels better.",
    "Positive mind, positive vibes, positive life.",
    "Happiness is a direction, not a place.",
    "Joy is what happens to us when we allow ourselves to recognize how good things really are.",
    "The most wasted of all days is one without laughter.",
    "Life is too important to be taken seriously.",
    "Lighten up, just enjoy life, smile more, laugh more, and don't get so worked up about things.",
    "The art of being happy lies in the power of extracting happiness from common things.",
    "A positive attitude gives you power over your circumstances instead of your circumstances having power over you.",
    "With the right attitude, self-imposed limitations vanish.",
    "If you have good thoughts they will shine out of your face like sunbeams and you will always look lovely.",
    "Keep smiling, because life is a beautiful thing and there's so much to smile about.",
    "Even the darkest night will end and the sun will rise.",
    "Nothing is impossible, the word itself says 'I'm possible'.",
    "Try to be a rainbow in someone else's cloud.",
    "No act of kindness, no matter how small, is ever wasted.",
    "Not all of us can do great things. But we can do small things with great love.",
    "At the end of the day, it's not the shoes you wore or the car you drove but the way you made others feel.",
    "Carry out a random act of kindness, with no expectation of reward.",
    "In a gentle way, you can shake the world.",
    "There is nothing either good or bad, but thinking makes it so.",
    "Whether you think you can, or you think you can't — you're right.",
    "I am not a product of my circumstances. I am a product of my decisions.",
    "Every strike brings me closer to the next home run.",
    "Definiteness of purpose is the starting point of all achievement.",
    "Life isn't about finding yourself. Life is about creating yourself.",
    "Nothing in life is to be feared; it is only to be understood.",
    "I find that the harder I work, the more luck I seem to have.",
    "The pessimist sees difficulty in every opportunity. The optimist sees opportunity in every difficulty.",
    "Don't let yesterday take up too much of today.",
    "You learn more from failure than from success. Don't let it stop you.",
    "It's not whether you get knocked down; it's whether you get up.",
    "If you are working on something that you really care about, you don't have to be pushed.",
    "Entrepreneurs are great at dealing with uncertainty and also very good at adjusting to changing situations.",
    "I have not failed. I've just found 10,000 ways that won't work.",
    "A successful man is one who can lay a firm foundation with the bricks others have thrown at him.",
    "No one can make you feel inferior without your consent.",
    "The whole secret of a successful life is to find out what is one's destiny to do, and then do it.",
    "If you're not positive energy, you're negative energy.",
    "Winning isn't everything, but wanting to win is.",
    "You can't go back and change the beginning, but you can start where you are and change the ending.",
    "People who are crazy enough to think they can change the world are the ones who do.",
    "Failure will never overtake me if my determination to succeed is strong enough.",
]

SELF_IMPROVEMENT_BASE = [
    "Be yourself, but always your better self.",
    "Growth begins at the end of your comfort zone.",
    "The only person you should try to be better than is the person you were yesterday.",
    "Invest in yourself. It pays the best interest.",
    "Small daily improvements over time lead to stunning results.",
    "You are always one decision away from a totally different life.",
    "Your life does not get better by chance. It gets better by change.",
    "The expert in anything was once a beginner.",
    "Don't wish for it. Work for it.",
    "Discipline is the bridge between goals and accomplishment.",
    "An investment in knowledge pays the best dividends.",
    "The capacity to learn is a gift; the ability to learn is a skill; the willingness to learn is a choice.",
    "Education is the most powerful weapon you can use to change the world.",
    "The more that you read, the more things you will know.",
    "Anyone who stops learning is old, whether at twenty or eighty.",
    "Real learning comes about when the competitive spirit has ceased.",
    "The beautiful thing about learning is that no one can take it away from you.",
    "You don't have to be perfect to be amazing.",
    "Make yourself a priority. At the end of the day, you're your longest commitment.",
    "Self-care is not selfish. You cannot serve from an empty vessel.",
    "Be so good they can't ignore you.",
    "Your habits will determine your future.",
    "Success is not final; failure is not fatal. It is the courage to continue that counts.",
    "The secret of your future is hidden in your daily routine.",
    "Focus on being productive instead of busy.",
    "Don't count the days; make the days count.",
    "The difference between who you are and who you want to be is what you do.",
    "Every action you take is a vote for the type of person you wish to become.",
    "Strive for progress, not perfection.",
    "You must do the things you think you cannot do.",
]

GRATITUDE_BASE = [
    "Gratitude turns what we have into enough.",
    "Be thankful for what you have; you'll end up having more.",
    "Gratitude is the healthiest of all human emotions.",
    "The more grateful I am, the more beauty I see.",
    "Count your blessings, not your problems.",
    "Gratitude is not only the greatest of virtues, but the parent of all others.",
    "Enough is a feast. Appreciate what you have.",
    "Feeling gratitude and not expressing it is like wrapping a present and not giving it.",
    "Joy is the simplest form of gratitude.",
    "Gratitude makes sense of our past, brings peace for today, and creates a vision for tomorrow.",
    "Start each day with a grateful heart.",
    "Be present in all things and thankful for all things.",
    "Appreciate the little things, for one day you may look back and realize they were the big things.",
    "Let us rise up and be thankful.",
    "The roots of all goodness lie in the soil of appreciation for goodness.",
    "A moment of gratitude makes a difference in your attitude.",
    "When I started counting my blessings, my whole life turned around.",
    "Gratitude is a powerful catalyst for happiness.",
    "Find beauty in the ordinary.",
    "There is always, always, always something to be thankful for.",
    "This is a wonderful day. I've never seen this one before.",
    "The way to happiness: keep your heart free from hate, your mind from worry, live simply, expect little, give much.",
    "Happiness cannot be traveled to, owned, earned, worn, or consumed.",
    "For every minute you are angry you lose sixty seconds of happiness.",
    "Happiness is when what you think, what you say, and what you do are in harmony.",
    "The purpose of our lives is to be happy.",
    "Be happy for this moment. This moment is your life.",
    "I am grateful for what I am and have. My thanksgiving is perpetual.",
    "Enjoy the little things in life, because one day you'll look back and realize they were the big things.",
    "Not what we say about our blessings, but how we use them, is the true measure of our thanksgiving.",
]

ENCOURAGEMENT_BASE = [
    "You've got this. Keep going.",
    "Someone believes in you today. Let that someone be you.",
    "You are stronger than you think.",
    "When things get hard, remember why you started.",
    "Every day is a fresh start.",
    "You have the power to change your story.",
    "Your potential is endless.",
    "You are capable of amazing things.",
    "Tough times never last, but tough people do.",
    "You are closer than you think.",
    "Keep going. Your breakthrough is coming.",
    "Don't give up. The beginning is always the hardest.",
    "Every expert was once a beginner. Keep learning.",
    "You've survived 100% of your worst days.",
    "Be proud of how far you've come.",
    "It's okay to not be okay. You'll get through this.",
    "You are doing better than you think.",
    "One step at a time. You'll get there.",
    "Your story isn't over yet.",
    "Progress is progress, no matter how small.",
    "You are exactly where you need to be.",
    "Your best days are still ahead of you.",
    "You have everything you need to get started.",
    "Today's struggles are building tomorrow's strength.",
    "Be gentle with yourself. You are a work in progress.",
    "You don't have to have it all figured out to move forward.",
    "Keep planting seeds. Your harvest is coming.",
    "You matter more than you know.",
    "The world needs your unique gifts.",
    "Not every day will be good, but there is good in every day.",
]

MEME_CAPTIONS_BASE = [
    "Me on Monday: I'm going to be so productive this week!\nMe on Friday: Did I even put pants on?",
    "My alarm: 6:00 AM\nMe setting 14 more alarms: just in case.",
    "Adulting is mostly just Googling things and hoping for the best.",
    "I don't always go the extra mile, but when I do, I took the wrong exit.",
    "My brain at 2AM: Remember that embarrassing thing from 2012? Let's replay it.",
    "Me opening the fridge for the 10th time hoping food magically appeared.",
    "Current status: Holding it together with coffee and optimism.",
    "I asked for a sign. Now there are signs everywhere. I regret this.",
    "My motivation level: 0%.\nMy snack level: 100%.",
    "Sorry I'm late, I didn't want to come.",
    "Me at 11:59 PM: I'll start being productive at midnight!\nMe at 12:01 AM: 😴",
    "Pro tip: Putting things in a 'safe place' means losing them forever.",
    "My spirit animal is a napping cat in a sunbeam.",
    "Plot twist: The weekend goes faster than the week.",
    "Me: I'll just rest my eyes for 5 minutes. Brain: Installing 8-hour update.",
    "Signs you're an adult: You get excited about buying new sponges.",
    "My inner child and I are both very excited about this pizza.",
    "Technically I was ready on time. I just wasn't ready to leave.",
    "Hydration? I prefer to run on caffeine and chaos.",
    "Current mood: Positive on the outside, searching for the remote on the inside.",
    "Life hack: Always carry a book so people think you're busy and don't talk to you.",
    "My house is a museum of good intentions.",
    "Someday I'll have my life together. Today is not that day, but someday.",
    "I don't have a bucket list but my worry list is pages long.",
    "Woke up this morning feeling great... then I remembered I have to adult.",
    "My brain: Let's go! My body: Let's not and say we did.",
    "Introvert level: Made plans, now hoping they get cancelled.",
    "The bags under my eyes are designer, I'll have you know.",
    "I'm not lazy. I'm on energy-saving mode.",
    "When you realize it's only Wednesday. 😮",
]

ENGAGEMENT_QUESTIONS_BASE = [
    "What's one small thing you're grateful for today? 💛",
    "What would you do if you knew you couldn't fail?",
    "What's the best piece of advice you've ever received?",
    "What's your go-to way to lift your mood on a bad day?",
    "Morning person or night owl? Tell us your superpower! 🦉☀️",
    "What's one habit that changed your life for the better?",
    "If you could send a message to your younger self, what would you say?",
    "What's something you've been putting off that you should do today?",
    "Who is someone that makes your world a little brighter? Tag them! ✨",
    "What does 'success' mean to you in one word?",
    "What book has most influenced your thinking?",
    "Coffee or tea? This is important. ☕🍵",
    "What's the kindest thing someone has done for you recently?",
    "What are you looking forward to this week?",
    "What's one goal you're working toward right now? Share below!",
    "Weekend plans? Big or small, we want to hear! 🎉",
    "What's one thing that always makes you smile?",
    "Describe your perfect morning in 3 words.",
    "What skill do you wish you had learned earlier in life?",
    "What does your ideal self look like? How close are you getting?",
]

# ────────────────────────────────────────────────────────
# EXPANDERS — generate variations to reach target counts
# ────────────────────────────────────────────────────────

PREFIXES = [
    "Remember: ", "Always know that ", "Never forget: ", "Believe this: ",
    "Truth: ", "Fact: ", "Today's reminder: ", "Worth repeating: ",
]
SUFFIXES = [
    " — start today.", " — you've got this.", " — believe it.", " — share this!",
    " — keep going.", " — spread this.", " — pass it on.",
]
TIME_PHRASES = ["Every morning", "Each new day", "Right now", "This very moment"]


def expand_list(base: list, target: int, category: str) -> list:
    """Expand a base list to reach the target count with variations."""
    result = list(base)
    attempts = 0
    while len(result) < target and attempts < target * 10:
        attempts += 1
        original = random.choice(base)
        variation_type = random.randint(0, 4)

        if variation_type == 0:
            new = random.choice(PREFIXES) + original.lower()
        elif variation_type == 1:
            new = original + random.choice(SUFFIXES)
        elif variation_type == 2:
            words = original.split()
            if len(words) > 4:
                new = " ".join(words[:3]) + "... " + " ".join(words[-2:])
            else:
                new = original
        elif variation_type == 3:
            new = f"[{category}] {original}"
        else:
            new = original

        if new not in result:
            result.append(new)

    # fill remaining with numbered originals if needed
    while len(result) < target:
        result.append(f"{random.choice(base)} #{len(result)}")

    return result[:target]


def build_library():
    print("📚 Generating content library...")

    library = {
        "motivational_quotes": expand_list(MOTIVATIONAL_BASE, 500, "Motivational"),
        "positive_life_quotes": expand_list(POSITIVE_LIFE_BASE, 500, "Positive"),
        "self_improvement_quotes": expand_list(SELF_IMPROVEMENT_BASE, 300, "SelfImprovement"),
        "gratitude_quotes": expand_list(GRATITUDE_BASE, 300, "Gratitude"),
        "encouragement_quotes": expand_list(ENCOURAGEMENT_BASE, 300, "Encouragement"),
        "meme_captions": expand_list(MEME_CAPTIONS_BASE, 300, "Meme"),
        "engagement_questions": expand_list(ENGAGEMENT_QUESTIONS_BASE, 200, "Engagement"),
    }

    # Write per-category files
    os.makedirs("content/quotes", exist_ok=True)
    os.makedirs("content/memes", exist_ok=True)
    os.makedirs("content/questions", exist_ok=True)

    categories_map = {
        "content/quotes/motivational.json": library["motivational_quotes"],
        "content/quotes/positive_life.json": library["positive_life_quotes"],
        "content/quotes/self_improvement.json": library["self_improvement_quotes"],
        "content/quotes/gratitude.json": library["gratitude_quotes"],
        "content/quotes/encouragement.json": library["encouragement_quotes"],
        "content/memes/captions.json": library["meme_captions"],
        "content/questions/engagement.json": library["engagement_questions"],
    }

    for path, data in categories_map.items():
        with open(path, "w") as f:
            json.dump({"items": data, "total": len(data)}, f, indent=2)
        print(f"  ✅ {path}: {len(data)} items")

    # Master library
    with open("content/library.json", "w") as f:
        totals = {k: len(v) for k, v in library.items()}
        json.dump({"totals": totals, "library": library}, f, indent=2)

    print(f"\n✅ Library generated! Total items: {sum(len(v) for v in library.values())}")
    return library


if __name__ == "__main__":
    build_library()
