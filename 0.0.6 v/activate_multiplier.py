import re

with open('Cryptonia.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add multiplier activation to show_crash_screen function
pattern = r'(def show_crash_screen\(self\):\n        \"\"\".*?\"\"\"\n        self\.hide_main_menu\(\)\n        self\.hide_earn_screen\(\)\n        self\.hide_casino_screen\(\)\n        self\.hide_trading_screen\(\)\n        \n        self\.current_state = GameState\.CRASH_SCREEN)'

replacement = r'''\1
        
        # Reset and start multiplier
        self.crash_multiplier = 1.01
        self.crash_multiplier_speed = 0.001
        self.crash_multiplier_active = True
        self.crash_max_stop_time = random.uniform(3.0, 8.0)
        self.crash_current_time = 0.0'''

content = re.sub(pattern, replacement, content, flags=re.DOTALL)

with open('Cryptonia.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Added multiplier activation to show_crash_screen')
