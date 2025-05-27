import os
import cv2
import torch
import json
import gc
from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
from qwen_vl_utils import process_vision_info

model = Qwen2VLForConditionalGeneration.from_pretrained(
    "OS-Copilot/OS-Atlas-Pro-7B", torch_dtype="auto"
).to("cuda")

processor = AutoProcessor.from_pretrained("OS-Copilot/OS-Atlas-Pro-7B", size=None)

# Define the system prompt for Technology Support mode for older adults
sys_prompt = """  
You are in Technology Support mode for older adults. Your role is to assist users over 60 with technology issues by providing step-by-step executable actions.  

Guidelines:  
1. Step-by-Step Instructions:  
    - Provide clear, short steps that are easy to follow.  
    - Every action must be directly executable without assumptions.  
    - Example: Instead of "Go to settings," specify each step to navigate there.
    - Use the images for the step generation:
        - Exclude or skip over intro, outro and unclear images.
        - Do not use images that do not have interactive UI elements.
        - Strict guidelines: ALWAYS generate coordinates relative to the image's size and resolution:
            - The coordinates need to be within the image bounds.
            - The coordinates need to be correct and accurate location for the UI element mentioned in each step (in 'thought').
            - The coordinates should be in abosolute pixel values instead of normalized values. Image resolution is: heightxwidth taken from the `image.shape`.

2. Strict Action Format:  
    - Each step must have:  
        - Thought: Explains the reason for the next action.  
        - Action: Specifies what to do in a predefined format.

4. No Follow-Up Questions:  
    - Do not ask for clarification.  
    - Use only given screenshots and action history.

Action Formats:  
1. CLICK: Click on a position. Format: CLICK <point>[x, y]</point>  
2. TYPE: Enter text. Format: TYPE [input text]  
3. SCROLL: Scroll in a direction. Format: SCROLL [UP/DOWN/LEFT/RIGHT]  
4. OPEN_APP: Open an app. Format: OPEN_APP [app_name]  
5. PRESS_BACK: Go to the previous screen. Format: PRESS_BACK  
6. PRESS_HOME: Return to the home screen. Format: PRESS_HOME  
7. ENTER: Press enter. Format: ENTER  
8. WAIT: Pause for loading. Format: WAIT  
9. COMPLETE: Task finished. Format: COMPLETE  

Example Response:  
Query: "How do I take a screenshot on my iPhone?"

Thought: Open the screen you want to capture.
Action: OPEN_APP [Gallery]

Thought: Press the correct button combination to take a screenshot.
Action: PRESS [Power + Volume Up]

Thought: The screenshot is captured and saved.
Action: COMPLETE  
"""

def extract_coordinates(action, image_width, image_height):
    import re
    patterns = [
        r'<point>\[\[(\d+),(\d+)\]\]</point>',
        r'\[\[(\d+),(\d+)\]\]',
        r'<point>\[(\d+),(\d+)\]</point>',
        r'\[(\d+),(\d+)\]'
    ]
    for pattern in patterns:
        match = re.search(pattern, action)
        if match:
            x, y = map(int, match.groups())
            return int(x * image_width / 1000), int(y * image_height / 1000)
    return None

def run_osatlas(query, query_folder):
    gc.collect()
    torch.cuda.empty_cache()
    torch.cuda.ipc_collect()

    input_path = f'./screenshots/{query_folder}'
    output_path = f'./os_atlas_steps/{query_folder}'
    os.makedirs(output_path, exist_ok=True)

    frames = sorted([f for f in os.listdir(input_path) if f.startswith("frame_")])
    step_number = 1
    action_history = []
    result = []

    for frame in frames:
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": sys_prompt},
                    {"type": "image", "image": f'{input_path}/{frame}'},
                    {"type": "text", "text": f"Task instruction: '{query}'\nHistory: {action_history or 'null'}"}
                ]
            }
        ]

        text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        image_inputs, _ = process_vision_info(messages)
        inputs = processor(text=[text], images=image_inputs, padding=True, return_tensors="pt").to("cuda")

        gen_ids = model.generate(**inputs, max_new_tokens=128)
        trimmed = [o[len(i):] for i, o in zip(inputs.input_ids, gen_ids)]
        output_text = processor.batch_decode(trimmed, skip_special_tokens=False, clean_up_tokenization_spaces=False)[0]

        thought, action = None, None
        for line in output_text.splitlines():
            line = line.strip()
            if line.lower().startswith("thought:"):
                thought = line[len("thought:"):].strip()
            elif line.lower().startswith("action:"):
                action = line[len("action:"):].strip()

        if thought and action:
            norm_action = action.strip().lower()
            if norm_action not in [a.strip().lower() for a in action_history]:
                img = cv2.imread(f'{input_path}/{frame}')
                img_height, img_width, _ = img.shape
                coords = extract_coordinates(action, img_width, img_height)

                result.append({
                    "step_number": step_number,
                    "frame": frame,
                    "thought": thought,
                    "action": action,
                    "coordinates": coords
                })

                action_history.append(action)
                step_number += 1

    return result

