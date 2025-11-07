import os
import cv2
import torch
import json
import gc
import re
import numpy as np
from PIL import Image
import torchvision.transforms as T
from torchvision.transforms.functional import InterpolationMode
from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
from qwen_vl_utils import process_vision_info

model = None
processor = None

IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)

def cleanup_gpu_memory():
    gc.collect()
    torch.cuda.empty_cache()
    torch.cuda.ipc_collect()
    
    for i in range(3):
        gc.collect()
    
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.synchronize()

def check_gpu_memory():
    if not torch.cuda.is_available():
        return False, "CUDA not available"
    
    total_memory = torch.cuda.get_device_properties(0).total_memory
    allocated_memory = torch.cuda.memory_allocated(0)
    cached_memory = torch.cuda.memory_reserved(0)
    free_memory = total_memory - allocated_memory
    
    min_required = 2 * 1024**3
    return free_memory > min_required, f"Free memory: {free_memory / 1024**3:.2f} GB"

sys_prompt = """You are in Technology Support mode for older adults. Your role is to assist users over 60 with technology issues by providing step-by-step executable actions by looking at the images and query provided.

CRITICAL: You MUST use this exact format for EVERY response:
Thought: [Name the specific UI element and explain what clicking/interacting will do, and not just describe what you see. Read any text labels, button names, app names visible on screen]
Action: [What to do next]

DO NOT use "actions:" - ONLY use "Action:"

IMPORTANT THOUGHT GUIDELINES:
- Describe ONLY what you can actually see in the image
- Be precise and factual - don't make up elements that aren't there
- Use correct spelling and grammar
- Don't describe non-existent UI elements
- For the thought, focus on what the user needs to do, not the example values shown in the UI
- Always skip the step if there is no phone screen in the image, such as intro and outro frames, person in the video, plain background, etc. Return only "SKIP" for thought and action if it's an intro/outro frame with no actual mobile UI, or if thought and action are too generic
- NEVER click on tutorial annotations like hands, arrows, circles, or highlights - these are not actual UI elements. Return "SKIP" if the only action would be clicking on such annotations
- Be specific about what you see (e.g., "profile icon" not "circle with number 3")
- Refer to at least the last thought and action to frame your current thought and action
- If the current step's thought and action are similar to the last step's thoughts and actions, skip the current step to avoid repetition - VERY IMPORTANT
- Do not include a COMPLETE action as a middle step - ONLY use it for the final step
- Sometimes, the COMPLETE action is displayed as the final step but the image is not the final step - very important to check the image and thought and action to determine the final step
- Avoid repeating the same thought and action for multiple steps - very important - all steps should be unique and different

ACTION GUIDELINES:
- Click on the appropriate UI elements to complete the task
- Use CLICK <point>[x,y]</point> format with coordinates for clicking
- Provide clear, actionable steps
- Use COMPLETE instead of PRESS_HOME when the task is finished
- Only use PRESS_HOME if you need to return to home screen mid-task
- If the previous action was a SCROLL action and your current image shows the same screen, return "SKIP" to avoid redundant scrolling steps
- Multiple consecutive CLICK actions are valid and should be included, but consecutive SCROLL actions on the same screen should be skipped

Action Formats:
- CLICK <point>[x,y]</point> - Click on a specific location
- SCROLL - Scroll within the current view
- SLIDE [LEFT/RIGHT] <point>[x,y]</point> - Slide a slider or control (include coordinates of slider)
- OPEN_APP [AppName] - Open an application
- TYPE [text] - Type text (CRITICAL: use generic descriptions like "destination address", "your name", "email address", "your location", "phone number", etc. NEVER use specific addresses or values like "Home", "123 Main St", etc. Only use specific app names like "Uber" or "Amazon" when searching in app stores)
- WAIT - Wait for confirmation or processing (ONLY use when waiting for booking confirmation, payment processing, or any completion message)
- PRESS_BACK - Go back
- PRESS_HOME - Go to home screen (only if needed mid-task)
- COMPLETE - Task finished (use this for the final step)

Examples:
Thought: I can see the Settings app with various options including "Display & Brightness" and "General".
Action: CLICK <point>[400, 200]</point>

Thought: I can see a text size slider with a small 'A' on the left and large 'A' on the right.
Action: SLIDE [RIGHT] <point>[500, 800]</point>

Thought: I need to scroll up to find the Clock app which is located above the current view.
Action: SCROLL [UP] <point>[400, 300]</point>

Thought: I can see a search bar for entering your destination address to complete the booking.
Action: TYPE your destination address <point>[500, 400]</point>

Thought: I can see a login form with email and password fields.
Action: TYPE your email address <point>[500, 300]</point>

Thought: I can see a confirmation screen showing the booking is being processed.
Action: WAIT

Thought: Task completed successfully.
Action: COMPLETE

CRITICAL CONSISTENCY RULES:
 - If your action is SLIDE [LEFT], your thought must always describe sliding LEFT
 - If your action is SLIDE [RIGHT], your thought must always describe sliding RIGHT

BAD EXAMPLE (DO NOT DO THIS):
Thought: Type "Office" into the search field (WRONG - repeats placeholder)
Action: TYPE [your destination address] <point>[500, 400]</point>

GOOD EXAMPLE:
Thought: Enter your destination address in the search field
Action: TYPE [your destination address] <point>[500, 400]</point>

IMPORTANT:
- Always provide coordinates for CLICK and TYPE actions
- If applicable, provide coordinates for OPEN_APP, SCROLL, and SLIDE actions
 - For sliders, use SLIDE [LEFT/RIGHT] instead of SCROLL
 - Look at the image and identify the exact pixel coordinates of the UI element you want to interact with
- Use COMPLETE for final steps, not PRESS_HOME
"""

def build_transform(input_size):
    MEAN, STD = IMAGENET_MEAN, IMAGENET_STD
    transform = T.Compose([
        T.Lambda(lambda img: img.convert('RGB') if img.mode != 'RGB' else img),
        T.Resize((input_size, input_size), interpolation=InterpolationMode.BICUBIC),
        T.ToTensor(),
        T.Normalize(mean=MEAN, std=STD)
    ])
    return transform

def find_closest_aspect_ratio(aspect_ratio, target_ratios, width, height, image_size):
    best_ratio_diff = float('inf')
    best_ratio = (1, 1)
    area = width * height
    for ratio in target_ratios:
        target_aspect_ratio = ratio[0] / ratio[1]
        ratio_diff = abs(aspect_ratio - target_aspect_ratio)
        if ratio_diff < best_ratio_diff:
            best_ratio_diff = ratio_diff
            best_ratio = ratio
        elif ratio_diff == best_ratio_diff:
            if area > 0.5 * image_size * image_size * ratio[0] * ratio[1]:
                best_ratio = ratio
    return best_ratio

def dynamic_preprocess(image, min_num=1, max_num=6, image_size=448, use_thumbnail=True):
    orig_width, orig_height = image.size
    aspect_ratio = orig_width / orig_height

    target_ratios = set(
        (i, j) for n in range(min_num, max_num + 1) for i in range(1, n + 1) for j in range(1, n + 1) if
        i * j <= max_num and i * j >= min_num)
    target_ratios = sorted(target_ratios, key=lambda x: x[0] * x[1])

    target_aspect_ratio = find_closest_aspect_ratio(
        aspect_ratio, target_ratios, orig_width, orig_height, image_size)

    target_width = image_size * target_aspect_ratio[0]
    target_height = image_size * target_aspect_ratio[1]
    blocks = target_aspect_ratio[0] * target_aspect_ratio[1]

    resized_img = image.resize((target_width, target_height))
    processed_images = []
    for i in range(blocks):
        box = (
            (i % (target_width // image_size)) * image_size,
            (i // (target_width // image_size)) * image_size,
            ((i % (target_width // image_size)) + 1) * image_size,
            ((i // (target_width // image_size)) + 1) * image_size
        )
        split_img = resized_img.crop(box)
        processed_images.append(split_img)
    assert len(processed_images) == blocks
    if use_thumbnail and len(processed_images) != 1:
        thumbnail_img = image.resize((image_size, image_size))
        processed_images.append(thumbnail_img)
    return processed_images

def load_image_optimized(image_path, input_size=448, max_num=6):
    try:
        image = Image.open(image_path).convert('RGB')
        transform = build_transform(input_size=input_size)
        images = dynamic_preprocess(image, image_size=input_size, use_thumbnail=True, max_num=max_num)
        pixel_values = [transform(image) for image in images]
        pixel_values = torch.stack(pixel_values)
        return pixel_values
    except Exception as e:
        print(f"Error loading image {image_path}: {e}")
        return None

def load_model():
    global model, processor
    
    if model is not None and processor is not None:
        return model, processor
    
    has_memory, memory_info = check_gpu_memory()
    if not has_memory:
        print(f"Low GPU memory: {memory_info}")
        cleanup_gpu_memory()
        has_memory, memory_info = check_gpu_memory()
        
        if not has_memory:
            raise RuntimeError(f"Insufficient GPU memory: {memory_info}")
    
    cleanup_gpu_memory()
    
    os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'expandable_segments:True'
    
    try:
        print("Loading OS-Atlas Pro 7B model...")
        
        model = Qwen2VLForConditionalGeneration.from_pretrained(
            "OS-Copilot/OS-Atlas-Pro-7B", 
            torch_dtype=torch.bfloat16,
            low_cpu_mem_usage=True,
            trust_remote_code=True
        ).eval().cuda()

        processor = AutoProcessor.from_pretrained(
            "OS-Copilot/OS-Atlas-Pro-7B",
            trust_remote_code=True,
            use_fast=False
        )
        
        print("OS-Atlas Pro 7B model loaded successfully")
        
    except Exception as e:
        print(f"Failed to load model: {e}")
        raise e
    
    return model, processor

def unload_model():
    global model, processor
    
    if model is not None:
        del model
        model = None
    
    if processor is not None:
        del processor
        processor = None
    
    cleanup_gpu_memory()
    print("Model unloaded and memory cleaned")

def extract_coordinates(action, image_width, image_height):
    clean_action = action.replace("<|im_end|>", "").strip()
    
    patterns = [
        r'<point>\[\[(\d+),\s*(\d+)\]\]</point>',
        r'\[\[(\d+),\s*(\d+)\]\]',
        r'<point>\[(\d+),\s*(\d+)\]</point>',
        r'\[(\d+),\s*(\d+)\]',
        r'<point>(\d+),\s*(\d+)</point>',
        r'(\d+),\s*(\d+)',
        r'at coordinates \((\d+),\s*(\d+)\)',
        r'coordinates \((\d+),\s*(\d+)\)',
        r'\((\d+),\s*(\d+)\)',
        r'SCROLL\s+\[[^\]]+\]\s+<point>\[(\d+),\s*(\d+)\]</point>',
        r'SLIDE\s+\[[^\]]+\]\s+<point>\[(\d+),\s*(\d+)\]</point>',
        r'SCROLL\s+\[[^\]]+\]\s+\[(\d+),\s*(\d+)\]',
        r'SLIDE\s+\[[^\]]+\]\s+\[(\d+),\s*(\d+)\]',
    ]
    
    for i, pattern in enumerate(patterns):
        match = re.search(pattern, clean_action)
        if match:
            x, y = map(int, match.groups())
            
            if 0 <= x <= 1000 and 0 <= y <= 1000:
                abs_x = int(x * image_width / 1000)
                abs_y = int(y * image_height / 1000)
                return abs_x, abs_y
            
            elif 0 <= x <= 1 and 0 <= y <= 1:
                abs_x = int(x * image_width)
                abs_y = int(y * image_height)
                return abs_x, abs_y
            
            elif 0 <= x <= image_width and 0 <= y <= image_height and x <= 2000 and y <= 2000:
                return x, y
            
            elif 0 <= x <= 100 and 0 <= y <= 100:
                abs_x = int(x * image_width / 100)
                abs_y = int(y * image_height / 100)
                return abs_x, abs_y
            
            else:
                return None
    
    return None

def standardize_action_format(action):
    if not action:
        return action
    
    clean_action = action.replace("<|im_end|>", "").strip()
    
    coords = None
    patterns = [
        r'<point>\[\[(\d+),\s*(\d+)\]\]</point>',
        r'\[\[(\d+),\s*(\d+)\]\]',
        r'<point>\[(\d+),\s*(\d+)\]</point>',
        r'\[(\d+),\s*(\d+)\]',
        r'<point>(\d+),\s*(\d+)</point>',
        r'(\d+),\s*(\d+)',
        r'at coordinates \((\d+),\s*(\d+)\)',
        r'coordinates \((\d+),\s*(\d+)\)',
        r'\((\d+),\s*(\d+)\)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, clean_action)
        if match:
            coords = (int(match.group(1)), int(match.group(2)))
            break
    
    action_lower = clean_action.lower()
    
    if action_lower.startswith('click'):
        if coords:
            return f"CLICK at ({coords[0]}, {coords[1]})"
        else:
            # Debug: Show what the model actually output
            if len(clean_action) > 10:
                print(f"  [COORD PARSE FAILED] Action: '{clean_action[:100]}'")
            return "CLICK"
    
    elif action_lower.startswith('scroll'):
        if coords:
            return f"SCROLL at ({coords[0]}, {coords[1]})"
        else:
            return "SCROLL"
    
    elif action_lower.startswith('slide'):
        direction_match = re.search(r'\[(left|right)\]', action_lower)
        direction = direction_match.group(1).upper() if direction_match else ""
        if coords:
            return f"SLIDE {direction} at ({coords[0]}, {coords[1]})"
        else:
            return f"SLIDE {direction}"
    
    elif action_lower.startswith('open_app'):
        app_match = re.search(r'\[([^\]]+)\]', clean_action)
        app_name = app_match.group(1) if app_match else "App"
        return f"OPEN {app_name}"
    
    elif action_lower.startswith('type'):
        text_match = re.search(r'\[([^\]]+)\]', clean_action)
        text = text_match.group(1) if text_match else "text"
        return f"TYPE: {text}"
    
    elif action_lower.startswith('press_back'):
        return "PRESS BACK"
    
    elif action_lower.startswith('press_home'):
        return "PRESS HOME"
    
    elif action_lower.startswith('complete'):
        return "COMPLETE"
    
    elif action_lower.startswith('wait'):
        return "WAIT"
    
    return clean_action

def parse_osatlas_response(output_text):
    thought, action = None, None
    capturing_thought, capturing_action = False, False
    temp_thought, temp_action = [], []
    
    for line in output_text.splitlines():
        line = line.strip()
    
        if line.lower().startswith("thought:"):
            capturing_thought = True
            capturing_action = False
            # Just "thought:" on this line - extract any content after it
            thought_content = line[8:].strip()
            if thought_content:
                temp_thought.append(thought_content)
            continue
    
        elif (line.lower().startswith("action:") or line.lower().startswith("actions:")):
            capturing_thought = False
            capturing_action = True
            colon_index = line.find(":")
            action_content = line[colon_index + 1:].strip()
            if action_content:
                temp_action.append(action_content)
            continue
    
        # Check if "action:" appears in the line while capturing thought
        if capturing_thought:
            # Use case-insensitive search but find actual position
            action_pos_match = re.search(r'\bAction:\s*', line, re.IGNORECASE)
            if action_pos_match:
                action_pos = action_pos_match.start()
                thought_part = line[:action_pos].strip()
                if thought_part:
                    temp_thought.append(thought_part)
                # Find the actual colon to extract after it
                colon_pos = line.find(':', action_pos)
                if colon_pos != -1:
                    action_content = line[colon_pos + 1:].strip()
                    if action_content:
                        temp_action.append(action_content)
                capturing_thought = False
                capturing_action = True
                continue
        
        if capturing_thought:
            temp_thought.append(line)
        elif capturing_action:
            temp_action.append(line.replace("<|im_end|>", "").strip())
    
    thought = " ".join(temp_thought).strip() if temp_thought else None
    action = " ".join(temp_action).strip() if temp_action else None
    
    if not thought and action:
        thought = f"Perform action: {standardize_action_format(action)}"
    
    if action:
        action = standardize_action_format(action)
    
    # Debug logging
    if not thought or not action:
        print(f"  [PARSE DEBUG] thought='{thought}', action='{action}', temp_thought={temp_thought}, temp_action={temp_action}")
        print(f"  [PARSE DEBUG] Full output lines: {[l.strip() for l in output_text.splitlines()]}")
    
    return thought, action

def draw_bounding_box(image, coordinates, step_number, action_type):
    if coordinates is None:
        return image
    
    x, y = coordinates
    height, width = image.shape[:2]
    
    if x < 0 or x >= width or y < 0 or y >= height:
        return image
    
    img_with_box = image.copy()
    
    box_size_x = min(120, int(width * 0.15))
    box_size_y = min(120, int(height * 0.15))
    
    top_left = (max(0, x - box_size_x // 2), max(0, y - box_size_y // 2))
    bottom_right = (min(width, x + box_size_x // 2), min(height, y + box_size_y // 2))
    
    color = (0, 255, 0)
    shadow_color = (0, 180, 0)
    
    shadow_top_left = (top_left[0] + 2, top_left[1] + 2)
    shadow_bottom_right = (bottom_right[0] + 2, bottom_right[1] + 2)
    cv2.rectangle(img_with_box, shadow_top_left, shadow_bottom_right, shadow_color, thickness=6)
    
    cv2.rectangle(img_with_box, top_left, bottom_right, color, thickness=6)
    
    inner_margin = 3
    inner_top_left = (top_left[0] + inner_margin, top_left[1] + inner_margin)
    inner_bottom_right = (bottom_right[0] - inner_margin, bottom_right[1] - inner_margin)
    cv2.rectangle(img_with_box, inner_top_left, inner_bottom_right, color, thickness=2)
    
    cv2.circle(img_with_box, (x, y), 8, (255, 255, 255), -1)
    cv2.circle(img_with_box, (x, y), 8, color, thickness=3)
    
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = max(0.8, min(width, height) / 800)
    font_thickness = 3
    
    text = f"Step {step_number}"
    text_size = cv2.getTextSize(text, font, font_scale, font_thickness)[0]
    
    text_margin = 15
    if top_left[1] > text_size[1] + text_margin:
        text_pos = (top_left[0], top_left[1] - text_margin)
    else:
        text_pos = (top_left[0], bottom_right[1] + text_size[1] + text_margin)
    
    text_padding = 8
    text_bg_top_left = (text_pos[0] - text_padding, text_pos[1] - text_size[1] - text_padding)
    text_bg_bottom_right = (text_pos[0] + text_size[0] + text_padding, text_pos[1] + text_padding)
    
    shadow_text_pos = (text_pos[0] + 2, text_pos[1] + 2)
    cv2.rectangle(img_with_box, 
                  (text_bg_top_left[0] + 2, text_bg_top_left[1] + 2),
                  (text_bg_bottom_right[0] + 2, text_bg_bottom_right[1] + 2),
                  (0, 0, 0), -1)
    
    cv2.rectangle(img_with_box, text_bg_top_left, text_bg_bottom_right, (255, 255, 255), -1)
    cv2.rectangle(img_with_box, text_bg_top_left, text_bg_bottom_right, color, thickness=2)
    
    cv2.putText(img_with_box, text, text_pos, font, font_scale, (0, 0, 0), font_thickness)
    
    return img_with_box


def run_osatlas_optimized(query, video_id, yield_progress=None):
    print(f"Starting OS-Atlas processing for {video_id}")
    
    model, processor = load_model()
    cleanup_gpu_memory()
    
    input_path = f'output/videos/{video_id}/ui-screens'
    output_path = f'output/videos/{video_id}/os_atlas_steps'
    os.makedirs(output_path, exist_ok=True)

    if not os.path.exists(input_path):
        print(f"UI screens folder {input_path} does not exist")
        return []
    
    frames = sorted([f for f in os.listdir(input_path) if f.startswith("frame_")])
    if not frames:
        print(f"No frame files found in {input_path}")
        return []
    
    print(f"Processing {len(frames)} frames")
    
    result = []
    step_number = 1
    action_history = []
    step_history = []  # Store (thought, action) tuples for context
    steps_with_coords = 0
    steps_with_thought_action = 0
    duplicate_steps_filtered = 0
    frames_processed = 0
    action_types = {}
    
    for i, frame in enumerate(frames):
        print(f"Processing frame {i+1}/{len(frames)}: {frame}")
        
        # Position-based intro/outro skipping only for longer videos (20+ frames)
        # Shorter videos (<20 frames, typically <60s) usually don't have intro/outro
        if len(frames) >= 20:
            intro_cutoff = max(2, int(len(frames) * 0.15))
            outro_start = max(0, len(frames) - max(1, int(len(frames) * 0.05)))
            
            skip_intro = i < intro_cutoff
            skip_outro = i >= outro_start
            if skip_intro or skip_outro:
                print(f"  Skipping frame {i+1} - intro/outro position")
                continue
        
        if yield_progress and (i + 1) % 3 == 0:
            yield_progress("osatlas-processing", "active", f"Processing frame {i+1}/{len(frames)}: {frame}")
        
        img_path = f'{input_path}/{frame}'
        pixel_values = load_image_optimized(img_path, max_num=6)
        
        if pixel_values is None:
            continue
        
        # Add context about previous steps to help model avoid duplicates
        context_text = ""
        if len(step_history) > 0:
            recent_steps = step_history[-3:] if len(step_history) >= 3 else step_history
            step_descriptions = []
            for prev_thought, prev_action in recent_steps:
                if prev_thought and prev_action:
                    step_descriptions.append(f"Thought: {prev_thought[:100]}... Action: {prev_action}")
            if step_descriptions:
                context_text = f"\nPrevious steps:\n" + "\n".join(f"- {desc}" for desc in step_descriptions)
        
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": sys_prompt},
                    {"type": "image", "image": img_path},
                    {"type": "text", "text": f"Task: {query}\n\nLook at the image carefully and describe EXACTLY what you see. Be accurate and factual - don't make up elements that aren't there. Use correct spelling and grammar.{context_text}\n\nFormat: Thought: [accurate description of what you see] Action: CLICK <point>[x,y]</point>"}
                ]
            }
        ]

        try:
            text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            
            image_inputs, _ = process_vision_info(messages)
            inputs = processor(text=[text], images=image_inputs, padding=True, return_tensors="pt").to("cuda")

            generation_config = dict(
                max_new_tokens=1024, 
                do_sample=True,
                temperature=0.1,
                top_p=0.9,
                repetition_penalty=1.1
            )
            
            gen_ids = model.generate(**inputs, **generation_config, pad_token_id=processor.tokenizer.eos_token_id)
            trimmed = [o[len(i):] for i, o in zip(inputs.input_ids, gen_ids)]
            output_text = processor.batch_decode(trimmed, skip_special_tokens=False, clean_up_tokenization_spaces=False)[0]
            
            thought, action = parse_osatlas_response(output_text)
            frames_processed += 1
            
            if not thought or not action:
                print(f"  Skipping frame {i+1} - failed to parse response")
                print(f"  Raw output: {output_text[:500]}")
                continue
            
            thought_lower = thought.lower().strip()
            action_lower = action.lower().strip()
            
            low_value_patterns = [
                "the video content shows",
                "the screen shows",
                "the screen displays",
                "the phone displays",
                "the image shows",
                "the image displays",
                "a phone displaying",
                "displaying settings for",
                "focusing on",
                "specifically focusing on"
            ]
            
            is_low_value_thought = any(pattern in thought_lower for pattern in low_value_patterns)
            
            # Content-based intro/outro detection - only for longer videos and only before steps start
            # Shorter videos typically jump right into the tutorial
            if len(frames) >= 20 and step_number == 1 and i < 5:
                intro_frame_patterns = [
                    "no screen visible",
                    "no phone visible",
                    "title card",
                    "title screen",
                    "intro screen",
                    "channel intro",
                    "subscribe button",
                    "youtube intro"
                ]
                
                is_intro_frame = any(pattern in thought_lower for pattern in intro_frame_patterns)
                
                if is_intro_frame:
                    print(f"  Skipping frame {i+1} - detected intro content")
                    continue
            
            # Handle COMPLETE actions - only allow on the last frame
            if 'complete' in action_lower:
                if i == len(frames) - 1:
                    # Last frame with COMPLETE - this is valid
                    action = "COMPLETE"
                    thought = "Task completed successfully"
                    action_lower = "complete"
                else:
                    # COMPLETE on a middle frame - skip it
                    print(f"Skipping COMPLETE action on middle frame {i+1}/{len(frames)}")
                    continue
            
            if 'press' in action_lower and 'home' in action_lower:
                if i == len(frames) - 1:
                    action = "COMPLETE"
                    thought = "Task completed successfully"
                    action_lower = "complete"
                elif is_low_value_thought:
                    continue
            
            if is_low_value_thought and not ('complete' in action_lower or 'press' in action_lower):
                print(f"  Skipping frame {i+1} - low value thought")
                continue
            
            # Handle SKIP responses from the model
            if 'skip' in action_lower or 'skip' in thought_lower:
                print(f"  Skipping frame {i+1} - model returned SKIP")
                continue
            
            action_clean = action_lower.replace('_', ' ').replace('-', ' ')
            is_scroll = action_lower.startswith('scroll')
            is_click = 'click' in action_clean and action_lower.startswith('click')
            is_wait = action_lower.startswith('wait')
            
            # Skip consecutive SCROLL actions
            if is_scroll and len(action_history) > 0:
                last_action = action_history[-1].lower()
                if 'scroll' in last_action:
                    print(f"  Skipping frame {i+1} - consecutive SCROLL action")
                    duplicate_steps_filtered += 1
                    continue

            # Skip consecutive WAIT actions
            if is_wait and len(action_history) > 0:
                last_action = action_history[-1].strip().lower()
                if last_action.startswith('wait'):
                    print(f"  Skipping frame {i+1} - consecutive WAIT action")
                    duplicate_steps_filtered += 1
                    continue
            
            # Skip if thought is exactly the same as the previous step
            if len(step_history) > 0 and thought:
                prev_thought, prev_action = step_history[-1]
                if prev_thought and thought.strip().lower() == prev_thought.strip().lower():
                    print(f"  Skipping frame {i+1} - duplicate thought: '{thought[:60]}...'")
                    duplicate_steps_filtered += 1
                    continue
            
            img = cv2.imread(img_path)
            if img is None:
                continue
                
            img_height, img_width, _ = img.shape
            coords = extract_coordinates(action, img_width, img_height)
            
            if thought and action:
                steps_with_thought_action += 1
            
            action_type = "unknown"
            if is_click:
                action_type = "click"
            elif is_scroll:
                action_type = "scroll"
            elif 'slide' in action_clean and action_lower.startswith('slide'):
                action_type = "slide"
            elif 'type' in action_clean and action_lower.startswith('type'):
                action_type = "type"
            elif 'press' in action_clean and 'back' in action_clean:
                action_type = "press_back"
            elif 'press' in action_clean and 'home' in action_clean:
                action_type = "press_home"
            elif 'open' in action_clean and 'app' in action_clean:
                action_type = "open_app"
            elif 'complete' in action_clean:
                action_type = "complete"
            elif is_wait:
                action_type = "wait"
            
            action_types[action_type] = action_types.get(action_type, 0) + 1
            
            must_have_coords = ['click', 'slide', 'type']
            never_need_coords = ['open_app', 'press_back', 'press_home', 'complete', 'wait']
            requires_coords = any(action_lower.startswith(action_type) for action_type in must_have_coords)
            never_needs_coords = any(action_lower.startswith(action_type) for action_type in never_need_coords) or is_scroll
            
            if coords:
                steps_with_coords += 1
            
            # Skip actions that require coordinates if coordinates are missing
            if requires_coords and not coords:
                print(f"  Skipping frame {i+1} - {action_type} action missing coordinates")
                print(f"  Raw action output: {action}")
                continue
                
            step_folder = os.path.join(output_path, f'step_{step_number:02d}')
            os.makedirs(step_folder, exist_ok=True)
            
            if coords:
                img_with_box = draw_bounding_box(img, coords, step_number, action)
                cv2.imwrite(os.path.join(step_folder, frame), img_with_box)
            else:
                # Save original image when no coordinates are needed or provided
                cv2.imwrite(os.path.join(step_folder, frame), img)
            
            step_details = {
                "step_number": step_number,
                "frame": frame,
                "thought": thought or "",
                "action": action,
                "coordinates": coords
            }
            
            with open(os.path.join(step_folder, 'step_details.json'), 'w') as f:
                json.dump(step_details, f, indent=2)
            
            if coords:
                box_width = min(120, int(img_width * 0.15))
                box_height = min(120, int(img_height * 0.15))
            else:
                box_width = box_height = 100
            
            result.append({
                "step": step_number,
                "action": action,
                "boundingBox": {
                    "x": coords[0] if coords else 0,
                    "y": coords[1] if coords else 0,
                    "width": box_width,
                    "height": box_height
                },
                "image": f"/api-vnava22/images/{video_id}/step_{step_number:02d}/{frame}",
                "thought": thought or ""
            })
            
            action_history.append(action)
            step_history.append((thought, action))
            
            print(f"Step {step_number}: {action}")
            step_number += 1
            
            cleanup_gpu_memory()
            
        except Exception as e:
            print(f"Error processing {frame}: {e}")
            continue
    
    cleanup_gpu_memory()
    
    total_steps = len(result)
    steps_with_coords_percent = (steps_with_coords / total_steps * 100) if total_steps > 0 else 0
    steps_complete_percent = (steps_with_thought_action / total_steps * 100) if total_steps > 0 else 0
    
    metrics = {
        "total_steps": total_steps,
        "steps_with_coordinates": steps_with_coords,
        "steps_with_coordinates_percent": round(steps_with_coords_percent, 2),
        "steps_with_thought_and_action": steps_with_thought_action,
        "steps_complete_percent": round(steps_complete_percent, 2),
        "duplicate_steps_filtered": duplicate_steps_filtered,
        "frames_processed": frames_processed,
        "action_type_distribution": action_types
    }
    
    return result, metrics

def run_osatlas(query, video_id):
    result, metrics = run_osatlas_optimized(query, video_id)
    return result

def run_osatlas_with_progress(query, video_id, yield_progress=None):
    result, metrics = run_osatlas_optimized(query, video_id, yield_progress)
    return result, metrics