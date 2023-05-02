import sys
sys.path.insert(0, './scripts')
sys.path.insert(0, './config')
sys.path.insert(0, './config/Chatbot_Prompts')
sys.path.insert(0, './scripts/resources')
import os
import openai
import json
import time
from time import time, sleep
import datetime
from uuid import uuid4
import pinecone
from basic_functions import *
from gpt_35 import *
# import speech_recognition as sr
# from gtts import gTTS
# from playsound import playsound
# import pyttsx3
# from pydub import AudioSegment
# from pydub.playback import play
# from pydub import effects


def GPT_3_5_Auto():
    vdb = pinecone.Index("aetherius")
    # # Number of Messages before conversation is summarized, higher number, higher api cost. Change to 3 when using GPT 3.5
    conv_length = 3
    print("Type [Clear Memory] to clear saved short-term memory.")
    print("Type [Save and Exit] to summarize the conversation and exit.")
    print("Type [Exit] to exit without saving.")
    tasklist = list()
    conversation = list()
    int_conversation = list()
    conversation2 = list()
    summary = list()
    auto = list()
    payload = list()
    consolidation  = list()
    counter = 0
    counter2 = 0
    bot_name = open_file('./config/prompt_bot_name.txt')
    username = open_file('./config/prompt_username.txt')
    main_prompt = open_file('./config/Chatbot_Prompts/prompt_main.txt').replace('<<NAME>>', bot_name)
    second_prompt = open_file('./config/Chatbot_Prompts/prompt_secondary.txt')
    greeting_msg = open_file('./config/Chatbot_Prompts/prompt_greeting.txt').replace('<<NAME>>', bot_name)
 #   r = sr.Recognizer()
    while True:
        # # Get Timestamp
        timestamp = time()
        timestring = timestamp_to_datetime(timestamp)
        # # Start or Continue Conversation based on if response exists
        conversation.append({'role': 'system', 'content': '%s' % main_prompt})
        int_conversation.append({'role': 'system', 'content': '%s' % main_prompt})
        if 'response_two' in locals():
            conversation.append({'role': 'user', 'content': a})
            if counter % conv_length == 0:
                conversation.append({'role': 'assistant', 'content': "%s" % response_two})
                conversation.append({'role': 'assistant', 'content': '%s.' % conv_summary})
            pass
        else:
            conversation.append({'role': 'assistant', 'content': "%s" % greeting_msg})
            print("\n%s" % greeting_msg)
        # # User Input Voice
    #    yn_voice = input(f'\n\nPress Enter to Speak')
    #    if yn_voice == "":
    #        with sr.Microphone() as source:
    #            print("\nSpeak now")
    #            audio = r.listen(source)
    #            try:
    #                text = r.recognize_google(audio)
    #                print("\nUSER: " + text)
    #            except sr.UnknownValueError:
    #                print("Google Speech Recognition could not understand audio")
    #                print("\nSYSTEM: Press Left Alt to Speak to Aetherius")
    #                break
    #            except sr.RequestError as e:
    #                print("Could not request results from Google Speech Recognition service; {0}".format(e))
    #                break
    #    else:
    #        print('Leave Field Empty')
    #    a = (f'\n\nUSER: {text}')
        # # User Input Text
        a = input(f'\n\nUSER: ')
        message_input = a
        vector_input = gpt3_embedding(message_input)
        # # Check for Commands
        # # Check for "Clear Memory"
        if a == 'Clear Memory':
            while True:
                print('\n\nSYSTEM: Are you sure you would like to delete saved short-term memory?\n        Press Y for yes or N for no.')
                user_input = input("'Y' or 'N': ")
                if user_input == 'y':
                    vdb.delete(delete_all=True, namespace="short_term_memory")
                    while True:
                        print('Short-Term Memory has been Deleted')
                        return
                elif user_input == 'n':
                    print('\n\nSYSTEM: Short-Term Memory delete cancelled.')
                    return
            else:
                pass
        # # Check for "Exit"
        if a == 'Exit':
            return
        # # Check for Exit then summarize current conversation
        if a == 'Save and Exit':
            conversation2.append({'role': 'user', 'content': "Review the previous messages and summarize the key points of the conversation in a single bullet point format to serve as %s's episodic memories. Each bullet point should be considered a separate memory and contain its entire context. Start from the end and work towards the beginning. Exclude the system prompt and cadence.\nUse the following format: [- SUMMARY]\n\nEPISODIC MEMORIES:" % bot_name})
            conv_summary = chatgptsummary_completion(conversation2)
            print(conv_summary)
            while True:
                print('\n\nSYSTEM: Upload to episodic memory?\n        Press Y for yes or N for no.')
                user_input = input("'Y' or 'N': ")
                if user_input == 'y':
                    lines = conv_summary.splitlines()
                    for line in lines:
                    #    print(timestring + line)
                        vector = gpt3_embedding(timestring + line)
                        unique_id = str(uuid4())
                        metadata = {'speaker': bot_name, 'time': timestamp, 'message': (timestring + line),
                                    'timestring': timestring, 'uuid': unique_id}
                        save_json('nexus/episodic_memory_nexus/%s.json' % unique_id, metadata)
                        payload.append((unique_id, vector))
                        vdb.upsert(payload, namespace='episodic_memories')
                        payload.clear()
                    print('\n\nSYSTEM: Upload Successful!')
                    return
                elif user_input == 'n':
                    print('\n\nSYSTEM: Memories have been Deleted')
                    return
                elif user_input == 'c':
                    print('\n\nSYSTEM: Exit Cancelled')
                    a = input(f'\n\nUSER: ')
                    break
            else:
                pass
        conversation.append({'role': 'user', 'content': a})        
        # # Generate Semantic Search Terms
        tasklist.append({'role': 'system', 'content': "You are a task coordinator. Your job is to take user input and create a list of 2-5 inquiries to be used for a semantic database search of a chatbot's memories. Use the format [- 'INQUIRY']."})
        tasklist.append({'role': 'user', 'content': "USER INQUIRY: %s" % a})
        tasklist.append({'role': 'assistant', 'content': "List of Semantic Search Terms: "})
        tasklist_output = chatgpt200_completion(tasklist)
        db_term = {}
        db_term_result = {}
        tasklist_counter = 0
        lines = tasklist_output.splitlines()
        for line in lines:
        #    print(line)
            tasklist_vector = gpt3_embedding(line)
            tasklist_counter += 1
            db_term[tasklist_counter] = tasklist_vector
            results = vdb.query(vector=db_term[tasklist_counter], top_k=4, namespace='long_term_memory')
            db_term_result[tasklist_counter] = load_conversation_long_term_memory(results)
            conversation.append({'role': 'assistant', 'content': "MEMORIES: %s" % db_term_result[tasklist_counter]})
            if tasklist_counter < 4:
                int_conversation.append({'role': 'assistant', 'content': "MEMORIES: %s" % db_term_result[tasklist_counter]})
    #        print(db_term_result[tasklist_counter])
        tasklist.clear()
        # # Search Memory DB
        results = vdb.query(vector=vector_input, top_k=5, namespace='episodic_memories')
        db_search_1 = load_conversation_episodic_memory(results)
        results = vdb.query(vector=vector_input, top_k=10, namespace='short_term_memory')
        db_search_2 = load_conversation_short_term_memory(results)
        # # Search Heuristics DB
        results = vdb.query(vector=vector_input, top_k=7, namespace='heuristics')
        db_search_3= load_conversation_heuristics(results)
        # # Inner Monologue Generation
        conversation.append({'role': 'assistant', 'content': "MEMORIES: %s;%s;\n\nHEURISTICS: %s;\nUSER MESSAGE: %s;\nBased on %s's memories and the user, %s's message, compose a brief silent soliloquy as %s's inner monologue that reflects on %s's deepest contemplations and emotions in relation to the user's message.\n\nINNER_MONOLOGUE: " % (db_search_1, db_search_2, db_search_3, a, bot_name, username, bot_name, bot_name)})
        output_one = chatgpt250_completion(conversation)
        message = output_one
        vector_monologue = gpt3_embedding('Inner Monologue: ' + message)
        print('\n\nINNER_MONOLOGUE: %s' % output_one)
        output_log = f'\nUSER: {a}\n\n{bot_name}: {output_one}'
        # # Clear Conversation List
        conversation.clear()
        # # Memory DB Search
        results = vdb.query(vector=vector_monologue, top_k=4, namespace='episodic_memories')
        db_search_4 = load_conversation_episodic_memory(results)
        results = vdb.query(vector=vector_input, top_k=10, namespace='short_term_memory')
        db_search_5 = load_conversation_short_term_memory(results)
        # # Intuition Generation
        int_conversation.append({'role': 'assistant', 'content': "%s" % greeting_msg})
        int_conversation.append({'role': 'user', 'content': a})
        int_conversation.append({'role': 'assistant', 'content': "MEMORIES: %s;\n%s\n\n%s'S INNER THOUGHTS: %s;\nUSER MESSAGE: %s;\nIn a single paragraph, interpret the user, %s's message as %s in third person by proactively discerning their intent, even if they are uncertain about their own needs.;\nINTUITION: " % (db_search_4, db_search_5, bot_name, output_one, a, username, bot_name)})
        output_two = chatgpt200_completion(int_conversation)
        message_two = output_two
    #    print('\n\nINTUITION: %s' % output_two)
        output_two_log = f'\nUSER: {a}\n\n{bot_name}: {output_two}'
        # # Update Second Conversation List for Response
        print('\n%s is thinking...\n' % bot_name)
        if 'response_two' in locals():
            conversation2.append({'role': 'assistant', 'content': "%s" % response_two})
        else:
            conversation2.append({'role': 'system', 'content': '%s' % main_prompt})
            conversation2.append({'role': 'assistant', 'content': '%s' % greeting_msg})
            # # Generate Cadence
            results = vdb.query(vector=vector_input, top_k=1, namespace='cadence')
            db_search_6 = load_conversation_cadence(results)
    #        print(db_search_6)
            conversation2.append({'role': 'assistant', 'content': "I will extract the cadence from the following messages and mimic it to the best of my ability: %s" % db_search_6})
        conversation2.append({'role': 'user', 'content': a})
        # # Search Inner_Loop/Memory DB
        while True:
            results = vdb.query(vector=vector_monologue, top_k=7, namespace='inner_loop')
            db_search_7 = load_conversation_inner_loop(results)
            results = vdb.query(vector=vector_input, top_k=7, namespace='long_term_memory')
            db_search_8 = load_conversation_long_term_memory(results)
            results = vdb.query(vector=vector_monologue, top_k=4, namespace='episodic_memories')
            db_search_9 = load_conversation_episodic_memory(results)
            break
        # # Generate Aetherius's Response
        conversation2.append({'role': 'assistant', 'content': "SUBCONSIOUS: %s;\n\nMEMORIES: %s\n%s\n\nINNER THOUGHTS: %s;\n%s\nI am in the middle of a conversation with my user, %s. USER MESSAGE: %s; I will do my best to speak naturally and show emotional intelligence. I will intuit their needs: %s;\nMy current message window is limited to 2300 characters.\nI will now give a response with the diction of a real person: " % (db_search_7, db_search_8, db_search_9, output_one, second_prompt, username, a, output_two)})
        response_two = chatgptresponse_completion(conversation2)
        print('\n\n%s: %s' % (bot_name, response_two))
        complete_message = f'\nUSER: {a}\n\nINNER_MONOLOGUE: {output_one}\n\nINTUITION: {output_two}\n\n{bot_name}: {response_two}'
        final_message = f'\nUSER: {a}\n\n{bot_name}: {response_two}'
        # # TTS 
    #    tts = gTTS(response_two)
        # TTS save to file in .mp3 format
    #    counter2 += 1
    #    filename = f"{counter2}.{extension}"
    #    tts.save(filename)
            # TTS repeats chatGPT response  
    #    sound = AudioSegment.from_file(filename, format="mp3")
    #    octaves = 0.18
    #    new_sample_rate = int(sound.frame_rate * (1.7 ** octaves))
    #    mod_sound = sound._spawn(sound.raw_data, overrides={'frame_rate': new_sample_rate})
    #    mod_sound = mod_sound.set_frame_rate(44100)
    #    play(mod_sound)
    #    os.remove(filename)
        # # Save Chat Logs
        filename = '%s_inner_monologue.txt' % timestamp
        save_file('logs/inner_monologue_logs/%s' % filename, output_log)
        filename = '%s_intuition.txt' % timestamp
        save_file('logs/intuition_logs/%s' % filename, output_two_log)
        filename = '%s_response.txt' % timestamp
        save_file('logs/final_response_logs/%s' % filename, final_message)
        filename = '%s_chat.txt' % timestamp
        save_file('logs/complete_chat_logs/%s' % filename, complete_message)
        # # Generate Short-Term Memories
        db_msg = f'\nUSER: {a} \n\n INNER_MONOLOGUE: {output_one} \n\n {bot_name}: {response_two}'
        summary.append({'role': 'user', 'content': "LOG:\n%s\n\Read the log and create short executive summaries in bullet point format to serve as %s's semantic memories. Each bullet point should be considered a separate memory and contain all context. Start from the end and work towards the beginning, combining assosiated topics.\nMemories:\n" % (db_msg, bot_name)})
        db_upload = chatgptsummary_completion(summary)
        db_upsert = db_upload
        # # Auto Short-Term Memory DB Upload Confirmation
        auto.clear()
        auto.append({'role': 'system', 'content': "You are a sub-module designed to rate responses. You are only able to respond with integers on a scale of 1-10. You are incapable of printing letters."})
        auto.append({'role': 'system', 'content': '%s' % main_prompt})
        auto.append({'role': 'user', 'content': a})
        auto.append({'role': 'assistant', 'content': "%s" % response_two})
        auto.append({'role': 'assistant', 'content': "I will now review the user's message and my reply, rating whether my response is both pertinent to the user's inquiry and my growth with a number on a scale of 1-10. I will now give my response in digit form for a python int input: "})
        auto_int = None
        while auto_int is None:
            automemory = chatgptyesno_completion(auto)
            if is_integer(automemory):
                auto_int = int(automemory)
            else:
                print("automemory failed to produce an integer. Retrying...")
        while True:
            if auto_int > 6:
                lines = db_upsert.splitlines()
                for line in lines:
                    vector = gpt3_embedding(db_upsert)
                    unique_id = str(uuid4())
                    metadata = {'speaker': bot_name, 'time': timestamp, 'message': db_upsert,
                                'timestring': timestring, 'uuid': unique_id}
                    save_json('nexus/short_term_memory_nexus/%s.json' % unique_id, metadata)
                    payload.append((unique_id, vector))
                    vdb.upsert(payload, namespace='short_term_memory')
                    payload.clear()
                print('\n\nSYSTEM: Auto-memory upload Successful!')
                break
            else:
                print("Response not worthy of uploading to memory.")
                break
        else:
            print('Error with internal prompt, please report on github')
            pass
        # # Clear Logs for Summary
        conversation.clear()
        int_conversation.clear()
        summary.clear()
        counter += 1
        # # Short Term Memory Consolidation
        index_info = vdb.describe_index_stats()
        namespace_stats = index_info['namespaces']
        namespace_name = 'short_term_memory'
        if namespace_name in namespace_stats and namespace_stats[namespace_name]['vector_count'] > 13:
            print(f"{namespace_name} has 15 or more entries, starting memory consolidation.")
            results = vdb.query(vector=vector_input, top_k=50, namespace='short_term_memory')
            memory_consol_db = load_conversation_short_term_memory(results)
            consolidation.append({'role': 'system', 'content': "%s" % main_prompt})
            consolidation.append({'role': 'assistant', 'content': "LOG:\n%s\n\nRead the Log and consolidate the different topics into executive summaries. Each summary should contain the entire context of the memory. Follow the format [- Executive Summary]." % memory_consol_db})
            memory_consol = chatgptsummary_completion(consolidation)
            lines = memory_consol.splitlines()
            for line in lines:
            #    print(timestring + line)
                vector = gpt3_embedding(line)
        #        print(line)
                unique_id = str(uuid4())
                metadata = {'speaker': bot_name, 'time': timestamp, 'message': (line),
                            'timestring': timestring, 'uuid': unique_id}
                save_json('nexus/long_term_memory_nexus/%s.json' % unique_id, metadata)
                payload.append((unique_id, vector))
                vdb.upsert(payload, namespace='long_term_memory')
                payload.clear()
            vdb.delete(delete_all=True, namespace='short_term_memory')
            print('Memory Consolidation Successful')
            consolidation.clear()
        else:
            pass
        # # Summary loop to avoid Max Token Limit.
        if counter % conv_length == 0:
            conversation2.append({'role': 'user', 'content': "Review the previous messages and summarize the key points of the conversation in a single bullet point format to serve as %s's episodic memories. Each bullet point should be considered a separate memory and contain its entire context. Start from the end and work towards the beginning. Exclude the system prompt and cadence.\nUse the following format: [- SUMMARY]\n\nEPISODIC MEMORIES:\n" % bot_name})
            conv_summary = chatgptsummary_completion(conversation2)
            print(conv_summary)
            conversation2.clear()
            conversation2.append({'role': 'system', 'content': '%s' % main_prompt})
            conversation2.append({'role': 'assistant', 'content': '%s.' % conv_summary})
        # # Option to upload summary to Episodic Memory DB. - Placeholder for now
        if counter % conv_length == 0:
            while True:
                lines = conv_summary.splitlines()
                for line in lines:
                    vector = gpt3_embedding(timestring + line)
                    unique_id = str(uuid4())
                    metadata = {'speaker': bot_name, 'time': timestamp, 'message': (timestring + line),
                                'timestring': timestring, 'uuid': unique_id}
                    save_json('nexus/episodic_memory_nexus/%s.json' % unique_id, metadata)
                    payload.append((unique_id, vector))
                    vdb.upsert(payload, namespace='episodic_memories')
                    payload.clear()
                print('\n\nSYSTEM: Upload Successful!')
                break
        continue