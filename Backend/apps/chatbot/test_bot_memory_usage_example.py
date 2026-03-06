"""
Example demonstration of bot_memory checking in prompts.

This script shows how the updated prompts use bot_memory to prevent
redundant questions and provide personalized responses.
"""


def demonstrate_property_selection():
    """Demonstrate property selection with bot_memory."""
    print("\n" + "="*80)
    print("EXAMPLE 1: Property Selection with Preferred Property")
    print("="*80)
    
    print("\n📝 Scenario: User has previously booked at 'Downtown Sports Center'")
    print("\nBot Memory:")
    print("  user_preferences:")
    print("    preferred_property: 6")
    print("    preferred_sport: 'tennis'")
    
    print("\n🤖 Without bot_memory checking:")
    print("  Bot: 'Which facility would you like to book?'")
    print("  Bot: [Shows list of all properties]")
    print("  User: 'Downtown Sports Center'")
    
    print("\n✅ With bot_memory checking (Task 19.2):")
    print("  Bot: 'I see you've booked at Downtown Sports Center before.")
    print("       Would you like to book there again?'")
    print("  User: 'Yes'")
    print("  Bot: [Skips property selection, proceeds to court selection]")
    
    print("\n💡 Benefit: Saved 1 interaction, faster booking flow")


def demonstrate_court_selection():
    """Demonstrate court selection with preferred sport."""
    print("\n" + "="*80)
    print("EXAMPLE 2: Court Selection with Preferred Sport")
    print("="*80)
    
    print("\n📝 Scenario: User prefers tennis courts")
    print("\nBot Memory:")
    print("  user_preferences:")
    print("    preferred_sport: 'tennis'")
    
    print("\n🤖 Without bot_memory checking:")
    print("  Bot: 'Here are the available courts:'")
    print("  Bot: '1. Tennis Court A'")
    print("  Bot: '2. Basketball Court B'")
    print("  Bot: '3. Tennis Court C'")
    print("  Bot: '4. Badminton Court D'")
    
    print("\n✅ With bot_memory checking (Task 19.2):")
    print("  Bot: 'I see you prefer tennis. We have 2 tennis courts available:'")
    print("  Bot: '1. Tennis Court A'")
    print("  Bot: '2. Tennis Court C'")
    print("  Bot: 'Which one would you like?'")
    
    print("\n💡 Benefit: Filtered results, more relevant options, faster selection")


def demonstrate_time_selection():
    """Demonstrate time selection with preferred time."""
    print("\n" + "="*80)
    print("EXAMPLE 3: Time Selection with Preferred Time")
    print("="*80)
    
    print("\n📝 Scenario: User prefers morning time slots")
    print("\nBot Memory:")
    print("  user_preferences:")
    print("    preferred_time: 'morning'")
    
    print("\n🤖 Without bot_memory checking:")
    print("  Bot: 'Here are the available time slots:'")
    print("  Bot: '1. 9:00 AM - 10:00 AM ($50/hour)'")
    print("  Bot: '2. 2:00 PM - 3:00 PM ($60/hour)'")
    print("  Bot: '3. 6:00 PM - 7:00 PM ($70/hour)'")
    
    print("\n✅ With bot_memory checking (Task 19.2):")
    print("  Bot: 'I see you prefer morning slots. Here are the morning options:'")
    print("  Bot: '1. 9:00 AM - 10:00 AM ($50/hour)'")
    print("  Bot: '2. 10:00 AM - 11:00 AM ($50/hour)'")
    print("  Bot: 'Would you like one of these?'")
    
    print("\n💡 Benefit: Prioritized relevant slots, personalized suggestions")


def demonstrate_information_query():
    """Demonstrate information query with preferred sport."""
    print("\n" + "="*80)
    print("EXAMPLE 4: Information Query with Preferred Sport")
    print("="*80)
    
    print("\n📝 Scenario: User has searched for tennis courts before")
    print("\nBot Memory:")
    print("  user_preferences:")
    print("    preferred_sport: 'tennis'")
    
    print("\n🤖 Without bot_memory checking:")
    print("  User: 'Show me courts'")
    print("  Bot: 'What sport are you interested in?'")
    print("  User: 'Tennis'")
    print("  Bot: [Shows tennis courts]")
    
    print("\n✅ With bot_memory checking (Task 19.2):")
    print("  User: 'Show me courts'")
    print("  Bot: 'I see you're interested in tennis. Here are our tennis facilities:'")
    print("  Bot: [Shows tennis courts immediately]")
    
    print("\n💡 Benefit: Eliminated 1 question, faster information retrieval")


def demonstrate_regular_user():
    """Demonstrate booking for regular user."""
    print("\n" + "="*80)
    print("EXAMPLE 5: Regular User Booking")
    print("="*80)
    
    print("\n📝 Scenario: User books regularly")
    print("\nBot Memory:")
    print("  inferred_information:")
    print("    booking_frequency: 'regular'")
    
    print("\n🤖 Without bot_memory checking:")
    print("  Bot: 'Here's your booking summary:'")
    print("  Bot: [Shows summary]")
    
    print("\n✅ With bot_memory checking (Task 19.2):")
    print("  Bot: 'Great to see you booking with us again! Here's your booking summary:'")
    print("  Bot: [Shows summary]")
    
    print("\n💡 Benefit: Personalized greeting, acknowledges loyalty")


def main():
    """Run all demonstrations."""
    print("\n" + "="*80)
    print("BOT MEMORY USAGE EXAMPLES - Task 19.2")
    print("="*80)
    print("\nThese examples show how the updated prompts use bot_memory to:")
    print("  1. Skip redundant questions")
    print("  2. Provide personalized suggestions")
    print("  3. Filter results based on preferences")
    print("  4. Acknowledge user history and loyalty")
    
    demonstrate_property_selection()
    demonstrate_court_selection()
    demonstrate_time_selection()
    demonstrate_information_query()
    demonstrate_regular_user()
    
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print("\nTask 19.2 implementation enables:")
    print("  ✅ Context-aware conversations")
    print("  ✅ Reduced redundancy")
    print("  ✅ Faster booking flows")
    print("  ✅ Personalized user experience")
    print("  ✅ Smart preference-based filtering")
    print("\nAll prompts now check bot_memory FIRST before asking questions!")
    print()


if __name__ == "__main__":
    main()
