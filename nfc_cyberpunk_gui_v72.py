#!/usr/bin/env python3
"""
NFC Business Card Programmer - CORA Style v7.2
DLT Secure Programmer - COMPACT UI + UNIVERSAL vCARD + SOUNDS

v7.2 Changes:
- CORA Provisioner color theme
- Unicode icons instead of emojis
- Timestamped log entries
- Professional dark styling
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import json
import struct
import datetime
import os
import threading
import math
import wave
import tempfile
from smartcard.System import readers
from smartcard.util import toHexString

# Crypto imports
try:
    from Crypto.Cipher import AES
    from Crypto.Random import get_random_bytes
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

# CORA COLOR SCHEME
BG_DARK = '#0d1117'
BG_CARD = '#161b22'
BG_INPUT = '#21262d'
CYAN = '#00d4ff'
MAGENTA = '#ff0099'
ORANGE = '#ff6b35'
GREEN = '#00ff88'
RED = '#ff4757'
YELLOW = '#ffd93d'
TEXT_WHITE = '#ffffff'
TEXT_GRAY = '#8b949e'
BORDER_COLOR = '#30363d'


# ============================================================================
# SOUND EFFECTS SYSTEM
# ============================================================================

class SoundManager:
    """Generate and play cyberpunk-style beep sounds"""
    
    def __init__(self):
        self.enabled = True
        self.sample_rate = 22050
        self.temp_dir = tempfile.gettempdir()
        
    def _generate_tone(self, frequency, duration, volume=0.5, fade=True):
        """Generate a sine wave tone"""
        n_samples = int(self.sample_rate * duration)
        samples = []
        
        for i in range(n_samples):
            t = i / self.sample_rate
            sample = math.sin(2 * math.pi * frequency * t) * volume
            
            # Apply fade in/out
            if fade:
                fade_samples = int(n_samples * 0.1)
                if i < fade_samples:
                    sample *= i / fade_samples
                elif i > n_samples - fade_samples:
                    sample *= (n_samples - i) / fade_samples
            
            # Convert to 16-bit integer
            samples.append(int(sample * 32767))
        
        return samples
    
    def _generate_multi_tone(self, freq_duration_pairs, volume=0.5):
        """Generate multiple tones in sequence"""
        all_samples = []
        for freq, duration in freq_duration_pairs:
            if freq == 0:  # Silence
                all_samples.extend([0] * int(self.sample_rate * duration))
            else:
                all_samples.extend(self._generate_tone(freq, duration, volume))
        return all_samples
    
    def _save_and_play(self, samples):
        """Save samples to WAV and play"""
        if not self.enabled:
            return
            
        try:
            # Create temp WAV file
            wav_path = os.path.join(self.temp_dir, f'nfc_beep_{id(samples)}.wav')
            
            with wave.open(wav_path, 'w') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(self.sample_rate)
                
                # Pack samples as 16-bit integers
                packed = struct.pack(f'<{len(samples)}h', *samples)
                wav_file.writeframes(packed)
            
            # Play based on platform
            if os.name == 'posix':
                if os.path.exists('/usr/bin/afplay'):  # macOS
                    os.system(f'afplay "{wav_path}" &')
                else:  # Linux
                    os.system(f'aplay -q "{wav_path}" &')
            else:  # Windows
                os.system(f'start /min "" "{wav_path}"')
                
        except Exception as e:
            pass  # Silently fail if sound doesn't work
    
    def play_async(self, sound_func):
        """Play sound in background thread"""
        thread = threading.Thread(target=sound_func, daemon=True)
        thread.start()
    
    # === SOUND EFFECTS ===
    
    def beep_click(self):
        """Short click for button press"""
        samples = self._generate_tone(1800, 0.03, 0.3)
        self._save_and_play(samples)
    
    def beep_tab(self):
        """Tab switch sound"""
        samples = self._generate_tone(1200, 0.02, 0.2)
        self._save_and_play(samples)
    
    def beep_auth_start(self):
        """Authentication starting - ascending tone"""
        samples = self._generate_multi_tone([
            (800, 0.05),
            (1000, 0.05),
            (1200, 0.05),
        ], 0.3)
        self._save_and_play(samples)
    
    def beep_auth_success(self):
        """Authentication successful - high double beep"""
        samples = self._generate_multi_tone([
            (1500, 0.08),
            (0, 0.03),
            (1800, 0.08),
        ], 0.4)
        self._save_and_play(samples)
    
    def beep_auth_fail(self):
        """Authentication failed - low descending"""
        samples = self._generate_multi_tone([
            (400, 0.1),
            (300, 0.15),
        ], 0.4)
        self._save_and_play(samples)
    
    def beep_write_start(self):
        """Write operation starting"""
        samples = self._generate_tone(1000, 0.05, 0.3)
        self._save_and_play(samples)
    
    def beep_write_chunk(self):
        """Writing chunk - quick tick"""
        samples = self._generate_tone(1400, 0.02, 0.2)
        self._save_and_play(samples)
    
    def beep_read(self):
        """Read operation - scanner sound"""
        samples = self._generate_multi_tone([
            (1200, 0.03),
            (1400, 0.03),
            (1200, 0.03),
        ], 0.3)
        self._save_and_play(samples)
    
    def beep_success(self):
        """Success - celebratory multi-tone"""
        samples = self._generate_multi_tone([
            (800, 0.08),
            (0, 0.02),
            (1000, 0.08),
            (0, 0.02),
            (1200, 0.08),
            (0, 0.02),
            (1600, 0.15),
        ], 0.5)
        self._save_and_play(samples)
    
    def beep_error(self):
        """Error - harsh buzz"""
        samples = self._generate_multi_tone([
            (200, 0.1),
            (0, 0.05),
            (200, 0.1),
            (0, 0.05),
            (150, 0.15),
        ], 0.5)
        self._save_and_play(samples)
    
    def beep_card_detected(self):
        """Card detected on reader"""
        samples = self._generate_multi_tone([
            (1000, 0.04),
            (1400, 0.06),
        ], 0.35)
        self._save_and_play(samples)
    
    def beep_preview(self):
        """Preview button"""
        samples = self._generate_multi_tone([
            (1100, 0.03),
            (1300, 0.03),
        ], 0.25)
        self._save_and_play(samples)
    
    def beep_save(self):
        """Save profile"""
        samples = self._generate_multi_tone([
            (1000, 0.05),
            (800, 0.08),
        ], 0.3)
        self._save_and_play(samples)
    
    def beep_load(self):
        """Load profile"""
        samples = self._generate_multi_tone([
            (800, 0.05),
            (1000, 0.08),
        ], 0.3)
        self._save_and_play(samples)
    
    def beep_clear(self):
        """Clear form"""
        samples = self._generate_tone(600, 0.08, 0.3)
        self._save_and_play(samples)
    
    def beep_program_start(self):
        """Program card button pressed - dramatic startup"""
        samples = self._generate_multi_tone([
            (400, 0.05),
            (600, 0.05),
            (800, 0.05),
            (1000, 0.05),
            (1200, 0.1),
        ], 0.4)
        self._save_and_play(samples)


# Global sound manager
sound = SoundManager()


# ============================================================================
# NTAG 424 DNA CRYPTO UTILITIES
# ============================================================================

def crc32_ntag(data):
    crc = 0xFFFFFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xEDB88320
            else:
                crc >>= 1
    return struct.pack('<I', crc ^ 0xFFFFFFFF)


def aes_cmac(key, data):
    cipher = AES.new(key, AES.MODE_ECB)
    L = cipher.encrypt(bytes(16))
    
    def shift_left_one(data):
        carry = 0
        result = bytearray(len(data))
        for i in range(len(data) - 1, -1, -1):
            new_carry = (data[i] >> 7) & 1
            result[i] = ((data[i] << 1) | carry) & 0xFF
            carry = new_carry
        return bytes(result)
    
    Rb = bytes([0x00] * 15 + [0x87])
    K1 = shift_left_one(L)
    if L[0] & 0x80:
        K1 = bytes(a ^ b for a, b in zip(K1, Rb))
    K2 = shift_left_one(K1)
    if K1[0] & 0x80:
        K2 = bytes(a ^ b for a, b in zip(K2, Rb))
    
    n = (len(data) + 15) // 16
    if n == 0:
        n = 1
    
    if len(data) == 0 or len(data) % 16 != 0:
        padded = data + bytes([0x80]) + bytes(16 - (len(data) % 16) - 1)
        M_last = bytes(a ^ b for a, b in zip(padded[-16:], K2))
    else:
        M_last = bytes(a ^ b for a, b in zip(data[-16:], K1))
    
    X = bytes(16)
    for i in range(n - 1):
        block = data[i*16:(i+1)*16]
        Y = bytes(a ^ b for a, b in zip(X, block))
        X = cipher.encrypt(Y)
    
    Y = bytes(a ^ b for a, b in zip(X, M_last))
    return cipher.encrypt(Y)


def derive_session_keys(key, rnd_a, rnd_b, ti):
    sv1_prefix = bytes([0xA5, 0x5A, 0x00, 0x01, 0x00, 0x80])
    sv1_data = sv1_prefix + rnd_a[0:2] + bytes(a ^ b for a, b in zip(rnd_a[2:8], rnd_b[0:6])) + rnd_b[6:16] + rnd_a[8:16]
    sv2_prefix = bytes([0x5A, 0xA5, 0x00, 0x01, 0x00, 0x80])
    sv2_data = sv2_prefix + rnd_a[0:2] + bytes(a ^ b for a, b in zip(rnd_a[2:8], rnd_b[0:6])) + rnd_b[6:16] + rnd_a[8:16]
    return aes_cmac(key, sv1_data), aes_cmac(key, sv2_data)


def calculate_mac_for_cmd(session_key_mac, ti, cmd_counter, cmd, cmd_data):
    ctr_bytes = struct.pack('<H', cmd_counter)
    mac_input = bytes([cmd]) + ctr_bytes + ti + cmd_data
    full_mac = aes_cmac(session_key_mac, mac_input)
    return bytes([full_mac[i] for i in range(1, 16, 2)])


def encrypt_data_for_write(session_key_enc, ti, cmd_counter, plaintext):
    crc = crc32_ntag(plaintext)
    data_with_crc = plaintext + crc
    pad_len = (16 - (len(data_with_crc) % 16)) % 16
    if pad_len == 0:
        pad_len = 16
    padded_data = data_with_crc + bytes([0x00] * pad_len)
    ctr_bytes = struct.pack('<H', cmd_counter)
    iv = ti + ctr_bytes + bytes(16 - len(ti) - 2)
    cipher = AES.new(session_key_enc, AES.MODE_CBC, iv)
    return cipher.encrypt(padded_data), len(padded_data)


def calculate_write_mac(session_key_mac, ti, cmd_counter, ins, header, encrypted_data):
    ctr_bytes = struct.pack('<H', cmd_counter)
    mac_input = bytes([ins]) + ctr_bytes + ti + header + encrypted_data
    full_mac = aes_cmac(session_key_mac, mac_input)
    return bytes([full_mac[i] for i in range(1, 16, 2)])


# ============================================================================
# MAIN GUI CLASS  
# ============================================================================

class CyberpunkNFCProgrammer:
    def __init__(self, root):
        self.root = root
        self.root.title("DLT SECURE NFC PROGRAMMER v7.2")
        self.root.geometry("1200x700")
        self.root.configure(bg=BG_DARK)
        self.root.resizable(True, True)
        
        # Session state
        self.session_key_enc = None
        self.session_key_mac = None
        self.ti = None
        self.cmd_counter = 0
        self.rnd_a = None
        self.rnd_b = None
        self.authenticated = False
        
        # Data storage
        self.phone_entries = []
        self.email_entries = []
        self.social_entries = []
        self.log_entries = []
        
        # Build UI
        self.setup_styles()
        self.create_ui()
        
        self.root.after(500, self.check_reader)
        
    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        style.configure('Cyber.TNotebook', background=BG_CARD, borderwidth=0)
        style.configure('Cyber.TNotebook.Tab', background=BG_INPUT, foreground=CYAN,
                       padding=[12, 6], font=('Consolas', 9, 'bold'))
        style.map('Cyber.TNotebook.Tab', background=[('selected', BG_CARD)],
                 foreground=[('selected', TEXT_WHITE)])
        
        style.configure('TCombobox', fieldbackground=BG_INPUT, background=BG_INPUT,
                       foreground=TEXT_WHITE, arrowcolor=CYAN)
        
    def create_ui(self):
        # Header
        header = tk.Frame(self.root, bg=BG_DARK, height=50)
        header.pack(fill=tk.X, padx=10, pady=5)
        header.pack_propagate(False)
        
        tk.Label(header, text="◇ NFC PROGRAMMER",
                font=('Consolas', 18, 'bold'), fg=CYAN, bg=BG_DARK).pack(side=tk.LEFT)
        tk.Label(header, text="v7.2", font=('Consolas', 12), fg=MAGENTA, bg=BG_DARK).pack(side=tk.LEFT, padx=10)
        
        # Status
        self.status_label = tk.Label(header, text="● Checking reader...", font=('Consolas', 10),
                                    fg=YELLOW, bg=BG_DARK)
        self.status_label.pack(side=tk.RIGHT)
        
        # Main content - 3 columns
        main = tk.Frame(self.root, bg=BG_DARK)
        main.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Left: Form with tabs (width ~400)
        left_frame = tk.Frame(main, bg=BG_CARD, width=420)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 5))
        left_frame.pack_propagate(False)
        
        self.create_form_tabs(left_frame)
        
        # Right: Log + Buttons (remaining space)
        right_frame = tk.Frame(main, bg=BG_CARD)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.create_log_panel(right_frame)
        
    def create_form_tabs(self, parent):
        # Form notebook
        self.form_notebook = ttk.Notebook(parent, style='Cyber.TNotebook')
        self.form_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Tab 1: Basic Info
        basic_tab = tk.Frame(self.form_notebook, bg=BG_CARD)
        self.form_notebook.add(basic_tab, text=' BASIC ')
        self.create_basic_tab(basic_tab)
        
        # Tab 2: Contact (Phone/Email)
        contact_tab = tk.Frame(self.form_notebook, bg=BG_CARD)
        self.form_notebook.add(contact_tab, text=' CONTACT ')
        self.create_contact_tab(contact_tab)
        
        # Tab 3: Social/Web
        social_tab = tk.Frame(self.form_notebook, bg=BG_CARD)
        self.form_notebook.add(social_tab, text=' SOCIAL ')
        self.create_social_tab(social_tab)
        
        # Bottom: Main action buttons
        btn_frame = tk.Frame(parent, bg=BG_CARD)
        btn_frame.pack(fill=tk.X, padx=5, pady=10)
        
        tk.Button(btn_frame, text="◉ PROVISION", command=self.program_card_with_sound,
                 bg=GREEN, fg='#000000', font=('Consolas', 12, 'bold'),
                 relief='flat', padx=20, pady=10, cursor='hand2').pack(fill=tk.X, pady=2)
        
        btn_row = tk.Frame(btn_frame, bg=BG_CARD)
        btn_row.pack(fill=tk.X, pady=5)
        
        tk.Button(btn_row, text="▼ Save", command=self.save_profile_with_sound, bg=BG_INPUT, fg=CYAN,
                 font=('Consolas', 9), relief='flat', padx=10, cursor='hand2').pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        tk.Button(btn_row, text="▲ Load", command=self.load_profile_with_sound, bg=BG_INPUT, fg=CYAN,
                 font=('Consolas', 9), relief='flat', padx=10, cursor='hand2').pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        tk.Button(btn_row, text="○ Clear", command=self.clear_form_with_sound, bg=BG_INPUT, fg=ORANGE,
                 font=('Consolas', 9), relief='flat', padx=10, cursor='hand2').pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        
    def create_basic_tab(self, parent):
        # Key input at top
        key_frame = tk.Frame(parent, bg=BG_CARD)
        key_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
        
        tk.Label(key_frame, text="◆ Auth Key", font=('Consolas', 9, 'bold'), fg=YELLOW, bg=BG_CARD,
                width=12, anchor='e').pack(side=tk.LEFT)
        
        self.entry_key = tk.Entry(key_frame, bg=BG_INPUT, fg=YELLOW, insertbackground=YELLOW,
                                 font=('Consolas', 10), relief='flat', width=35)
        self.entry_key.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        self.entry_key.insert(0, "00000000000000000000000000000000")  # Default key
        
        tk.Label(parent, text="(32 hex chars = 16 bytes)", font=('Consolas', 8), fg=TEXT_GRAY, 
                bg=BG_CARD).pack(anchor='e', padx=10)
        
        # Mode selector
        mode_frame = tk.Frame(parent, bg=BG_CARD)
        mode_frame.pack(fill=tk.X, padx=10, pady=(5, 10))
        
        tk.Label(mode_frame, text="◎ Mode", font=('Consolas', 9, 'bold'), fg=CYAN, bg=BG_CARD,
                width=12, anchor='e').pack(side=tk.LEFT)
        
        self.write_mode = tk.StringVar(value="url")
        ttk.Combobox(mode_frame, textvariable=self.write_mode, 
                    values=["url", "vcard"], width=10, state='readonly').pack(side=tk.LEFT, padx=5)
        
        tk.Label(mode_frame, text="url = newredcard.com link | vcard = direct contact", 
                font=('Consolas', 8), fg=TEXT_GRAY, bg=BG_CARD).pack(side=tk.LEFT, padx=5)
        
        fields = [
            ("Full Name*", "fullname"),
            ("First Name", "firstname"),
            ("Last Name", "lastname"),
            ("Title", "title"),
            ("Company", "company"),
            ("Department", "department"),
        ]
        
        for i, (label, attr) in enumerate(fields):
            row = tk.Frame(parent, bg=BG_CARD)
            row.pack(fill=tk.X, padx=10, pady=3)
            
            tk.Label(row, text=label, font=('Consolas', 9), fg=TEXT_GRAY, bg=BG_CARD,
                    width=12, anchor='e').pack(side=tk.LEFT)
            
            entry = tk.Entry(row, bg=BG_INPUT, fg=TEXT_WHITE, insertbackground=CYAN,
                           font=('Consolas', 10), relief='flat')
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
            setattr(self, f'entry_{attr}', entry)
        
        # Note field
        note_frame = tk.Frame(parent, bg=BG_CARD)
        note_frame.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(note_frame, text="Note", font=('Consolas', 9), fg=TEXT_GRAY, bg=BG_CARD,
                width=12, anchor='e').pack(side=tk.LEFT, anchor='n')
        
        self.text_note = tk.Text(note_frame, height=3, bg=BG_INPUT, fg=TEXT_WHITE,
                                insertbackground=CYAN, font=('Consolas', 10), relief='flat')
        self.text_note.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        
    def create_contact_tab(self, parent):
        # Phones section
        tk.Label(parent, text="◧ PHONES", font=('Consolas', 10, 'bold'), fg=CYAN,
                bg=BG_CARD).pack(anchor='w', padx=10, pady=(10, 5))
        
        self.phone_frame = tk.Frame(parent, bg=BG_CARD)
        self.phone_frame.pack(fill=tk.X, padx=10)
        
        self.add_phone_row()
        
        tk.Button(parent, text="+ Add Phone", command=self.add_phone_row, bg=BG_INPUT,
                 fg=GREEN, font=('Consolas', 8), relief='flat', cursor='hand2').pack(anchor='w', padx=10, pady=2)
        
        # Emails section
        tk.Label(parent, text="◈ EMAILS", font=('Consolas', 10, 'bold'), fg=CYAN,
                bg=BG_CARD).pack(anchor='w', padx=10, pady=(15, 5))
        
        self.email_frame = tk.Frame(parent, bg=BG_CARD)
        self.email_frame.pack(fill=tk.X, padx=10)
        
        self.add_email_row()
        
        tk.Button(parent, text="+ Add Email", command=self.add_email_row, bg=BG_INPUT,
                 fg=GREEN, font=('Consolas', 8), relief='flat', cursor='hand2').pack(anchor='w', padx=10, pady=2)
        
    def create_social_tab(self, parent):
        # Website
        row = tk.Frame(parent, bg=BG_CARD)
        row.pack(fill=tk.X, padx=10, pady=(10, 5))
        tk.Label(row, text="Website", font=('Consolas', 9), fg=TEXT_GRAY, bg=BG_CARD,
                width=10, anchor='e').pack(side=tk.LEFT)
        self.entry_website = tk.Entry(row, bg=BG_INPUT, fg=TEXT_WHITE, insertbackground=CYAN,
                                     font=('Consolas', 10), relief='flat')
        self.entry_website.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        
        # Social links
        tk.Label(parent, text="◉ SOCIAL LINKS", font=('Consolas', 10, 'bold'), fg=CYAN,
                bg=BG_CARD).pack(anchor='w', padx=10, pady=(15, 5))
        
        self.social_frame = tk.Frame(parent, bg=BG_CARD)
        self.social_frame.pack(fill=tk.X, padx=10)
        
        self.add_social_row()
        
        tk.Button(parent, text="+ Add Social", command=self.add_social_row, bg=BG_INPUT,
                 fg=GREEN, font=('Consolas', 8), relief='flat', cursor='hand2').pack(anchor='w', padx=10, pady=2)
        
    def create_log_panel(self, parent):
        # Top button bar
        btn_bar = tk.Frame(parent, bg=BG_CARD)
        btn_bar.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Label(btn_bar, text="◧ LOG", font=('Consolas', 10, 'bold'),
                fg=MAGENTA, bg=BG_CARD).pack(side=tk.LEFT)
        
        # Debug buttons
        debug_btns = [
            ("◆ Auth", self.test_auth_with_sound, CYAN),
            ("◧ Settings", self.debug_settings_with_sound, YELLOW),
            ("◨ Read", self.read_ndef_with_sound, GREEN),
            ("◈ Preview", self.preview_with_sound, ORANGE),
            ("○", self.clear_log_with_sound, RED),
        ]
        
        for text, cmd, color in reversed(debug_btns):
            tk.Button(btn_bar, text=text, command=cmd, bg=BG_INPUT, fg=color,
                     font=('Consolas', 8, 'bold'), relief='flat', padx=8,
                     cursor='hand2').pack(side=tk.RIGHT, padx=2)
        
        # Console
        self.console = scrolledtext.ScrolledText(parent, bg='#010409', fg=TEXT_WHITE,
                                                 font=('Consolas', 9), relief='flat',
                                                 insertbackground=CYAN)
        self.console.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Configure tags
        for tag, color in [('cyan', CYAN), ('magenta', MAGENTA), ('green', GREEN),
                          ('red', RED), ('yellow', YELLOW), ('orange', ORANGE), ('gray', TEXT_GRAY)]:
            self.console.tag_configure(tag, foreground=color)
        
        # Welcome message
        self.log_message("◇ NFC PROGRAMMER v7.2", CYAN)
        self.log_message("Ready to program NTAG 424 DNA cards", TEXT_GRAY)
        self.log_message("Fill in contact info - Click PROVISION", TEXT_GRAY)
        self.log_message("─" * 45, TEXT_GRAY)
        
    def add_phone_row(self):
        row = tk.Frame(self.phone_frame, bg=BG_CARD)
        row.pack(fill=tk.X, pady=2)
        
        type_var = tk.StringVar(value="WORK")
        ttk.Combobox(row, textvariable=type_var, values=["WORK", "CELL", "HOME"],
                    width=6, state='readonly').pack(side=tk.LEFT, padx=(0, 5))
        
        entry = tk.Entry(row, bg=BG_INPUT, fg=TEXT_WHITE, insertbackground=CYAN,
                        font=('Consolas', 10), relief='flat', width=25)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.phone_entries.append((type_var, entry))
        
    def add_email_row(self):
        row = tk.Frame(self.email_frame, bg=BG_CARD)
        row.pack(fill=tk.X, pady=2)
        
        type_var = tk.StringVar(value="WORK")
        ttk.Combobox(row, textvariable=type_var, values=["WORK", "HOME", "OTHER"],
                    width=6, state='readonly').pack(side=tk.LEFT, padx=(0, 5))
        
        entry = tk.Entry(row, bg=BG_INPUT, fg=TEXT_WHITE, insertbackground=CYAN,
                        font=('Consolas', 10), relief='flat', width=25)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.email_entries.append((type_var, entry))
        
    def add_social_row(self):
        row = tk.Frame(self.social_frame, bg=BG_CARD)
        row.pack(fill=tk.X, pady=2)
        
        platform_var = tk.StringVar(value="LinkedIn")
        ttk.Combobox(row, textvariable=platform_var, 
                    values=["LinkedIn", "Twitter", "GitHub", "Instagram", "Facebook"],
                    width=9, state='readonly').pack(side=tk.LEFT, padx=(0, 5))
        
        entry = tk.Entry(row, bg=BG_INPUT, fg=TEXT_WHITE, insertbackground=CYAN,
                        font=('Consolas', 10), relief='flat', width=25)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.social_entries.append((platform_var, entry))
        
    def log_message(self, msg, color=TEXT_WHITE):
        timestamp = datetime.datetime.now().strftime("[%H:%M:%S] ")
        tag = {CYAN: 'cyan', MAGENTA: 'magenta', GREEN: 'green', RED: 'red',
               YELLOW: 'yellow', ORANGE: 'orange', TEXT_GRAY: 'gray'}.get(color)
        self.console.insert(tk.END, timestamp, 'gray')
        self.console.insert(tk.END, msg + '\n', tag)
        self.console.see(tk.END)
        self.console.update()
        self.log_entries.append({'timestamp': datetime.datetime.now().isoformat(), 'message': msg})
        
    def clear_log(self):
        self.console.delete(1.0, tk.END)
        self.log_entries = []
    
    # === SOUND WRAPPER FUNCTIONS ===
    
    def program_card_with_sound(self):
        sound.play_async(sound.beep_program_start)
        self.program_card()
    
    def save_profile_with_sound(self):
        sound.play_async(sound.beep_save)
        self.save_profile()
    
    def load_profile_with_sound(self):
        sound.play_async(sound.beep_load)
        self.load_profile()
    
    def clear_form_with_sound(self):
        sound.play_async(sound.beep_clear)
        self.clear_form()
    
    def test_auth_with_sound(self):
        sound.play_async(sound.beep_click)
        self.test_auth_only()
    
    def debug_settings_with_sound(self):
        sound.play_async(sound.beep_click)
        self.debug_read_settings()
    
    def read_ndef_with_sound(self):
        sound.play_async(sound.beep_read)
        self.read_ndef_file()
    
    def preview_with_sound(self):
        sound.play_async(sound.beep_preview)
        self.preview_vcard()
    
    def clear_log_with_sound(self):
        sound.play_async(sound.beep_clear)
        self.clear_log()
        
    def clear_form(self):
        for attr in ['fullname', 'firstname', 'lastname', 'title', 'company', 'department', 'website']:
            getattr(self, f'entry_{attr}').delete(0, tk.END)
        self.text_note.delete("1.0", tk.END)
        self.log_message("Form cleared", TEXT_GRAY)
        
    def check_reader(self):
        try:
            r = readers()
            if r:
                name = str(r[0])[:30]
                self.status_label.config(text=f"● {name}", fg=GREEN)
            else:
                self.status_label.config(text="● No reader", fg=RED)
        except Exception as e:
            self.status_label.config(text=f"● Error", fg=RED)
        self.root.after(2000, self.check_reader)
        
    def generate_vcard(self):
        """Generate vCard with CRLF line endings"""
        CRLF = "\r\n"
        lines = ["BEGIN:VCARD", "VERSION:3.0"]
        
        fn = self.entry_fullname.get().strip()
        if not fn:
            first = self.entry_firstname.get().strip()
            last = self.entry_lastname.get().strip()
            fn = f"{first} {last}".strip() or "Contact"
        lines.append(f"FN:{fn}")
        
        ln = self.entry_lastname.get().strip()
        first = self.entry_firstname.get().strip()
        if ln or first:
            lines.append(f"N:{ln};{first};;;")
        
        if org := self.entry_company.get().strip():
            lines.append(f"ORG:{org}")
        if title := self.entry_title.get().strip():
            lines.append(f"TITLE:{title}")
        
        for t, p in self.phone_entries:
            if phone := p.get().strip():
                lines.append(f"TEL;TYPE={t.get()}:{phone}")
        
        for t, e in self.email_entries:
            if email := e.get().strip():
                lines.append(f"EMAIL;TYPE={t.get()}:{email}")
        
        if url := self.entry_website.get().strip():
            lines.append(f"URL:{url}")
        
        for p, u in self.social_entries:
            if url := u.get().strip():
                lines.append(f"URL;TYPE={p.get()}:{url}")
        
        if note := self.text_note.get("1.0", tk.END).strip():
            note = note.replace("\\", "\\\\").replace("\n", "\\n")
            lines.append(f"NOTE:{note}")
        
        lines.append("END:VCARD")
        return CRLF.join(lines)
    
    def generate_url(self, uid=""):
        """Generate newredcard.com URL with contact params"""
        import urllib.parse
        
        params = {}
        
        if fn := self.entry_fullname.get().strip():
            params['fn'] = fn
        if first := self.entry_firstname.get().strip():
            params['first'] = first
        if last := self.entry_lastname.get().strip():
            params['last'] = last
        if title := self.entry_title.get().strip():
            params['title'] = title
        if org := self.entry_company.get().strip():
            params['org'] = org
        
        # Get first phone and email
        for t, p in self.phone_entries:
            if phone := p.get().strip():
                params['phone'] = phone
                break
        
        for t, e in self.email_entries:
            if email := e.get().strip():
                params['email'] = email
                break
        
        if url := self.entry_website.get().strip():
            params['web'] = url
        
        # Get social links
        for p, u in self.social_entries:
            platform = p.get().lower()
            if url := u.get().strip():
                params[platform] = url
        
        if uid:
            params['uid'] = uid
        
        base_url = "https://newredcard.com/verify.html"
        query_string = urllib.parse.urlencode(params)
        return f"{base_url}?{query_string}"
        
    def preview_vcard(self):
        self.log_message("\n--- PREVIEW ───", MAGENTA)
        
        mode = self.write_mode.get()
        
        if mode == "url":
            # URL mode preview
            url = self.generate_url("XXXXXXX")
            self.log_message(f"Mode: URL (newredcard.com)", CYAN)
            self.log_message(f"\nURL:", TEXT_WHITE)
            self.log_message(f"  {url}", GREEN)
            
            url_without_prefix = url.replace("https://", "")
            url_bytes = url_without_prefix.encode('utf-8')
            ndef_rec = bytes([0xD1, 0x01, len(url_bytes) + 1, 0x55, 0x04]) + url_bytes
            ndef_data = struct.pack('>H', len(ndef_rec)) + ndef_rec
            
            self.log_message(f"\nNDEF Size: {len(ndef_data)} / 256 bytes", GREEN if len(ndef_data) <= 256 else RED)
        else:
            # vCard mode preview
            vcard = self.generate_vcard()
            vcard_bytes = vcard.encode('utf-8')
            
            self.log_message(f"Mode: vCard (direct contact)", CYAN)
            self.log_message(f"\nvCard Content:", TEXT_WHITE)
            for line in vcard.split('\r\n'):
                self.log_message(f"  {line}", TEXT_GRAY)
            
            mime = b'text/x-vcard'
            if len(vcard_bytes) <= 255:
                ndef_rec = bytes([0xD2, len(mime), len(vcard_bytes)]) + mime + vcard_bytes
            else:
                ndef_rec = bytes([0xC2, len(mime)]) + struct.pack('>I', len(vcard_bytes)) + mime + vcard_bytes
            ndef_data = struct.pack('>H', len(ndef_rec)) + ndef_rec
            
            self.log_message(f"\nNDEF Size: {len(ndef_data)} / 256 bytes", GREEN if len(ndef_data) <= 256 else RED)
        
    # ========================================================================
    # NTAG 424 DNA COMMANDS
    # ========================================================================
    
    def send_apdu(self, conn, apdu, desc=""):
        apdu_hex = ''.join([f'{b:02X}' for b in apdu])
        self.log_message(f"  >> {apdu_hex[:60]}{'...' if len(apdu_hex) > 60 else ''}", TEXT_GRAY)
        r, sw1, sw2 = conn.transmit(apdu)
        self.log_message(f"  << SW={sw1:02X}{sw2:02X}", TEXT_GRAY)
        return r, sw1, sw2
    
    def select_ndef_app(self, conn):
        self.log_message("Selecting NDEF app...", CYAN)
        apdu = [0x00, 0xA4, 0x04, 0x00, 0x07, 0xD2, 0x76, 0x00, 0x00, 0x85, 0x01, 0x01, 0x00]
        r, sw1, sw2 = self.send_apdu(conn, apdu)
        self.authenticated = False
        return sw1 == 0x90
    
    def get_auth_key(self):
        """Get authentication key from entry field"""
        key_hex = self.entry_key.get().strip().replace(" ", "").replace("-", "")
        if len(key_hex) != 32:
            self.log_message(f"Warning: Key must be 32 hex chars (got {len(key_hex)})", YELLOW)
            return bytes(16)  # Default
        try:
            return bytes.fromhex(key_hex)
        except ValueError:
            self.log_message("Warning: Invalid hex in key, using default", YELLOW)
            return bytes(16)
    
    def ev2_authenticate(self, conn, key_no=0, key=None):
        if key is None:
            key = self.get_auth_key()
        
        key_preview = key.hex()[:8] + "..." + key.hex()[-4:]
        self.log_message(f"Authenticating with key: {key_preview}", CYAN)
        
        # Part 1
        apdu = [0x90, 0x71, 0x00, 0x00, 0x02, key_no, 0x00, 0x00]
        r, sw1, sw2 = self.send_apdu(conn, apdu)
        if sw1 != 0x91 or sw2 != 0xAF:
            sound.play_async(sound.beep_auth_fail)
            self.log_message(f"Auth Part 1 failed: {sw1:02X}{sw2:02X}", RED)
            return False
        
        enc_rnd_b = bytes(r)
        cipher = AES.new(key, AES.MODE_CBC, bytes(16))
        self.rnd_b = cipher.decrypt(enc_rnd_b)
        self.rnd_a = get_random_bytes(16)
        rnd_b_rot = self.rnd_b[1:] + self.rnd_b[0:1]
        
        # Part 2
        cipher = AES.new(key, AES.MODE_CBC, bytes(16))
        enc_data = cipher.encrypt(self.rnd_a + rnd_b_rot)
        apdu = [0x90, 0xAF, 0x00, 0x00, len(enc_data)] + list(enc_data) + [0x00]
        r, sw1, sw2 = self.send_apdu(conn, apdu)
        
        if sw1 != 0x91 or sw2 != 0x00:
            sound.play_async(sound.beep_auth_fail)
            self.log_message(f"Auth Part 2 failed: {sw1:02X}{sw2:02X}", RED)
            return False
        
        # Parse response
        response = bytes(r)
        cipher = AES.new(key, AES.MODE_CBC, bytes(16))
        decrypted = cipher.decrypt(response)
        self.ti = decrypted[0:4]
        
        self.session_key_enc, self.session_key_mac = derive_session_keys(key, self.rnd_a, self.rnd_b, self.ti)
        self.cmd_counter = 0
        self.authenticated = True
        
        sound.play_async(sound.beep_auth_success)
        self.log_message(f"Authenticated (TI={self.ti.hex()})", GREEN)
        return True
    
    def get_file_settings(self, conn, file_no):
        if not self.authenticated:
            return None
        cmd = 0xF5
        params = bytes([file_no])
        mac = calculate_mac_for_cmd(self.session_key_mac, self.ti, self.cmd_counter, cmd, params)
        apdu = [0x90, cmd, 0x00, 0x00, 9] + list(params) + list(mac) + [0x00]
        r, sw1, sw2 = self.send_apdu(conn, apdu)
        self.cmd_counter += 1
        if sw1 == 0x91 and sw2 == 0x00 and len(r) >= 4:
            comm_names = {0x00: "Plain", 0x01: "MAC", 0x03: "Full"}
            self.log_message(f"  File {file_no:02X}: {comm_names.get(r[1], '?')}, Access={r[2]:02X}{r[3]:02X}", GREEN)
            return r[1]
        return None
    
    def write_data_plain_with_mac(self, conn, file_no, offset, data):
        if not self.authenticated:
            return False
        cmd = 0x8D
        offset_bytes = struct.pack('<I', offset)[:3]
        length_bytes = struct.pack('<I', len(data))[:3]
        params = bytes([file_no]) + offset_bytes + length_bytes + data
        mac = calculate_mac_for_cmd(self.session_key_mac, self.ti, self.cmd_counter, cmd, params)
        apdu = [0x90, cmd, 0x00, 0x00, len(params) + 8] + list(params) + list(mac) + [0x00]
        r, sw1, sw2 = self.send_apdu(conn, apdu)
        self.cmd_counter += 1
        if sw1 == 0x91 and sw2 == 0x00:
            return True
        else:
            error_msg = {0x7E: "Length", 0x9D: "Permission", 0xAE: "Auth", 0xBE: "Boundary"}.get(sw2, f"0x{sw2:02X}")
            self.log_message(f"  Write error: {error_msg}", RED)
            return False
    
    def write_data_iso_update(self, conn, offset, data):
        """Alternative: Use ISO UpdateBinary which may handle larger writes"""
        self.log_message(f"  Trying ISOUpdateBinary ({len(data)} bytes)...", TEXT_GRAY)
        
        # Select NDEF file by ID (E104)
        select_apdu = [0x00, 0xA4, 0x00, 0x00, 0x02, 0xE1, 0x04]
        r, sw1, sw2 = conn.transmit(select_apdu)
        
        if sw1 != 0x90:
            self.log_message(f"  File select failed: {sw1:02X}{sw2:02X}", RED)
            return False
        
        # Write in chunks of 54 bytes (ISO limit)
        pos = 0
        chunk_size = 54
        while pos < len(data):
            chunk = data[pos:pos + chunk_size]
            off = offset + pos
            
            if off < 256:
                update_apdu = [0x00, 0xD6, 0x00, off, len(chunk)] + list(chunk)
            else:
                update_apdu = [0x00, 0xD6, (off >> 8) & 0x7F, off & 0xFF, len(chunk)] + list(chunk)
            
            r, sw1, sw2 = conn.transmit(update_apdu)
            
            if sw1 != 0x90:
                self.log_message(f"  ISOUpdate failed at {pos}: {sw1:02X}{sw2:02X}", RED)
                return False
            
            pos += len(chunk)
        
        return True
    
    def write_data_chunked(self, conn, file_no, offset, data, chunk_size=32):
        """Write in small chunks - 32 bytes is safe for NTAG 424 DNA"""
        self.log_message(f"  Chunked write: {len(data)} bytes in {chunk_size}-byte chunks", TEXT_GRAY)
        total = 0
        chunk_num = 0
        while total < len(data):
            chunk = data[total:total + chunk_size]
            chunk_num += 1
            sound.play_async(sound.beep_write_chunk)
            self.log_message(f"  Chunk {chunk_num}: {len(chunk)} bytes at offset {offset + total}", TEXT_GRAY)
            if not self.write_data_plain_with_mac(conn, file_no, offset + total, chunk):
                return False
            total += len(chunk)
        return True
    
    # ========================================================================
    # DEBUG COMMANDS
    # ========================================================================
    
    def test_auth_only(self):
        self.log_message("\n--- TEST AUTH ───", MAGENTA)
        try:
            r = readers()
            if not r:
                self.log_message("No reader", RED)
                return
            conn = r[0].createConnection()
            conn.connect()
            if self.select_ndef_app(conn) and self.ev2_authenticate(conn):
                self.log_message("Auth successful!", GREEN)
            conn.disconnect()
        except Exception as e:
            self.log_message(f"Error: {e}", RED)
    
    def debug_read_settings(self):
        self.log_message("\n--- FILE SETTINGS ───", MAGENTA)
        try:
            r = readers()
            if not r:
                return
            conn = r[0].createConnection()
            conn.connect()
            if self.select_ndef_app(conn) and self.ev2_authenticate(conn):
                for f in [0x01, 0x02, 0x03]:
                    self.get_file_settings(conn, f)
            conn.disconnect()
        except Exception as e:
            self.log_message(f"Error: {e}", RED)
    
    def read_ndef_file(self):
        self.log_message("\n--- READ NDEF ───", MAGENTA)
        try:
            r = readers()
            if not r:
                return
            conn = r[0].createConnection()
            conn.connect()
            if not self.select_ndef_app(conn):
                return
            
            # Read first 128 bytes to get full NDEF message
            cmd = 0xAD
            params = bytes([0x02, 0x00, 0x00, 0x00, 0x80, 0x00, 0x00])  # Read 128 bytes
            apdu = [0x90, cmd, 0x00, 0x00, len(params)] + list(params) + [0x00]
            r_data, sw1, sw2 = self.send_apdu(conn, apdu)
            
            if sw1 == 0x91 and sw2 == 0x00:
                data = bytes(r_data)
                self.log_message(f"Raw ({len(data)} bytes): {data[:32].hex()}...", TEXT_GRAY)
                
                # Parse NDEF
                if len(data) >= 2:
                    nlen = (data[0] << 8) | data[1]
                    self.log_message(f"NDEF Length: {nlen} bytes", CYAN)
                    
                    if nlen > 0 and len(data) > 2:
                        ndef_msg = data[2:2+nlen]
                        
                        # Parse NDEF record header
                        if len(ndef_msg) >= 3:
                            header = ndef_msg[0]
                            mb = (header >> 7) & 1
                            me = (header >> 6) & 1
                            sr = (header >> 4) & 1
                            tnf = header & 0x07
                            
                            type_len = ndef_msg[1]
                            
                            if sr:  # Short record
                                payload_len = ndef_msg[2]
                                type_start = 3
                            else:  # Long record
                                payload_len = struct.unpack('>I', ndef_msg[2:6])[0]
                                type_start = 6
                            
                            rec_type = ndef_msg[type_start:type_start+type_len]
                            payload_start = type_start + type_len
                            payload = ndef_msg[payload_start:payload_start+payload_len]
                            
                            tnf_names = {1: "Well-known", 2: "Media", 4: "External"}
                            self.log_message(f"TNF: {tnf_names.get(tnf, tnf)}, Type: {rec_type}", CYAN)
                            self.log_message(f"Payload: {payload_len} bytes", CYAN)
                            
                            # Decode based on type
                            if rec_type == b'U':  # URL
                                prefixes = {
                                    0x00: "", 0x01: "http://www.", 0x02: "https://www.",
                                    0x03: "http://", 0x04: "https://"
                                }
                                prefix_code = payload[0] if payload else 0
                                url_part = payload[1:].decode('utf-8', errors='replace') if len(payload) > 1 else ""
                                full_url = prefixes.get(prefix_code, "") + url_part
                                self.log_message(f"URL: {full_url[:80]}{'...' if len(full_url) > 80 else ''}", GREEN)
                            elif b'vcard' in rec_type or b'text' in rec_type:
                                # vCard or text
                                text = payload.decode('utf-8', errors='replace')[:100]
                                self.log_message(f"Content: {text}...", GREEN)
                            else:
                                try:
                                    type_str = rec_type.decode('utf-8')
                                    self.log_message(f"Type: {type_str}", TEXT_GRAY)
                                except:
                                    self.log_message(f"Type: {rec_type.hex()}", TEXT_GRAY)
                                self.log_message(f"Payload: {payload[:50].hex()}...", GREEN)
            else:
                self.log_message(f"Read failed: {sw1:02X}{sw2:02X}", YELLOW)
            
            conn.disconnect()
        except Exception as e:
            self.log_message(f"Error: {e}", RED)
    
    # ========================================================================
    # MAIN PROGRAM
    # ========================================================================
    
    def program_card(self):
        self.log_message("\n" + "=" * 40, MAGENTA)
        self.log_message("PROVISIONING CARD", MAGENTA)
        self.log_message("=" * 40, MAGENTA)
        
        if not CRYPTO_AVAILABLE:
            self.log_message("pycryptodome not installed!", RED)
            return
        
        try:
            reader_list = readers()
            if not reader_list:
                self.log_message("No reader found!", RED)
                return
            
            conn = reader_list[0].createConnection()
            conn.connect()
            
            # Get UID
            r, sw1, sw2 = conn.transmit([0xFF, 0xCA, 0x00, 0x00, 0x00])
            if sw1 != 0x90:
                self.log_message("No card detected!", RED)
                conn.disconnect()
                return
            
            uid = bytes(r).hex().upper()
            sound.play_async(sound.beep_card_detected)
            self.log_message(f"Card UID: {uid}", CYAN)
            
            if len(r) != 7:
                self.log_message("NTAG 21x detected, using simple write", YELLOW)
                self.program_ntag_simple(conn)
                conn.disconnect()
                return
            
            self.log_message("NTAG 424 DNA detected", CYAN)
            
            if not self.select_ndef_app(conn):
                raise Exception("Select failed")
            
            # Try authentication first
            auth_success = self.ev2_authenticate(conn)
            
            if not auth_success:
                self.log_message("Warning: Auth failed (custom key?) - trying ISO write...", YELLOW)
            
            # Build NDEF based on mode
            mode = self.write_mode.get()
            self.log_message(f"Mode: {mode}", CYAN)
            
            if mode == "url":
                # URL mode - write link to newredcard.com/verify.html
                url = self.generate_url(uid)
                self.log_message(f"URL: {url[:50]}...", TEXT_GRAY)
                
                # URL NDEF record structure:
                # For Short Record (payload < 256 bytes):
                #   Header: D1 (MB=1, ME=1, CF=0, SR=1, IL=0, TNF=001)
                #   Type Length: 01
                #   Payload Length: 1 byte
                #   Type: 55 ('U' for URI)
                #   Payload: [prefix code] + [URI without prefix]
                #
                # Prefix codes: 0x00=none, 0x01=http://www., 0x02=https://www., 
                #               0x03=http://, 0x04=https://
                
                url_without_prefix = url.replace("https://", "")
                url_bytes = url_without_prefix.encode('utf-8')
                payload_len = len(url_bytes) + 1  # +1 for prefix byte
                
                if payload_len <= 255:
                    # Short record format
                    ndef_rec = bytes([
                        0xD1,           # Header: MB=1, ME=1, SR=1, TNF=001 (Well-known)
                        0x01,           # Type length: 1
                        payload_len,    # Payload length
                        0x55,           # Type: 'U' (URI)
                        0x04            # Prefix: https://
                    ]) + url_bytes
                else:
                    # Long record format (payload > 255)
                    ndef_rec = bytes([
                        0xC1,           # Header: MB=1, ME=1, SR=0, TNF=001
                        0x01,           # Type length: 1
                    ]) + struct.pack('>I', payload_len) + bytes([
                        0x55,           # Type: 'U'
                        0x04            # Prefix: https://
                    ]) + url_bytes
                
                self.log_message(f"URL payload: {payload_len} bytes", TEXT_GRAY)
            else:
                # vCard mode - write direct contact
                vcard = self.generate_vcard()
                vcard_bytes = vcard.encode('utf-8')
                self.log_message(f"vCard: {len(vcard_bytes)} bytes", TEXT_GRAY)
                
                mime = b'text/x-vcard'
                if len(vcard_bytes) <= 255:
                    ndef_rec = bytes([0xD2, len(mime), len(vcard_bytes)]) + mime + vcard_bytes
                else:
                    ndef_rec = bytes([0xC2, len(mime)]) + struct.pack('>I', len(vcard_bytes)) + mime + vcard_bytes
            
            ndef_data = struct.pack('>H', len(ndef_rec)) + ndef_rec
            
            self.log_message(f"NDEF size: {len(ndef_data)} bytes", CYAN)
            
            if len(ndef_data) > 256:
                self.log_message("Warning: Truncating to 256 bytes", YELLOW)
                ndef_data = ndef_data[:256]
            
            # Write strategies
            self.log_message("Writing...", CYAN)
            success = False
            
            # Strategy 1: If authenticated, try native write
            if auth_success:
                if len(ndef_data) <= 32:
                    success = self.write_data_plain_with_mac(conn, 0x02, 0, ndef_data)
                else:
                    success = self.write_data_chunked(conn, 0x02, 0, ndef_data, 32)
            
            # Strategy 2: Try ISO UpdateBinary (works without auth on some cards)
            if not success:
                self.log_message("  Trying ISO UpdateBinary...", TEXT_GRAY)
                self.select_ndef_app(conn)  # Re-select
                success = self.write_data_iso_update(conn, 0, ndef_data)
            
            if success:
                sound.play_async(sound.beep_success)
                self.log_message("=" * 40, GREEN)
                self.log_message("CARD PROVISIONED!", GREEN)
                self.log_message("=" * 40, GREEN)
                self.log_message(f"Serial: {uid}", TEXT_WHITE)
                self.log_message(f"Tap with phone to test", TEXT_GRAY)
                messagebox.showinfo("Success", f"Card programmed!\n{len(ndef_data)} bytes written")
            else:
                raise Exception("Write failed")
            
            conn.disconnect()
            
        except Exception as e:
            sound.play_async(sound.beep_error)
            self.log_message(f"Error: {e}", RED)
            messagebox.showerror("Error", str(e))
    
    def program_ntag_simple(self, conn):
        vcard = self.generate_vcard()
        vcard_bytes = vcard.encode('utf-8')
        mime = b'text/x-vcard'
        rec = bytes([0xD2, len(mime), len(vcard_bytes)]) + mime + vcard_bytes
        
        if len(rec) < 255:
            msg = bytes([0x03, len(rec)]) + rec
        else:
            msg = bytes([0x03, 0xFF, len(rec) >> 8, len(rec) & 0xFF]) + rec
        msg += bytes([0xFE])
        
        cc = bytes([0xE1, 0x40, 0x10, 0x00])
        data = cc + msg
        if len(data) % 4:
            data += bytes(4 - len(data) % 4)
        
        for i in range(len(data) // 4):
            block = 4 + i
            apdu = [0xFF, 0xD6, 0x00, block, 0x04] + list(data[i*4:(i+1)*4])
            r, sw1, sw2 = conn.transmit(apdu)
            if sw1 != 0x90:
                raise Exception(f"Write failed at block {block}")
        
        sound.play_async(sound.beep_success)
        self.log_message("NTAG programmed!", GREEN)
        messagebox.showinfo("Success", "Card programmed!")
    
    def save_profile(self):
        filename = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if filename:
            profile = {
                'fullname': self.entry_fullname.get(),
                'firstname': self.entry_firstname.get(),
                'lastname': self.entry_lastname.get(),
                'title': self.entry_title.get(),
                'company': self.entry_company.get(),
                'department': self.entry_department.get(),
                'note': self.text_note.get("1.0", tk.END).strip(),
                'website': self.entry_website.get(),
                'phones': [(t.get(), p.get()) for t, p in self.phone_entries],
                'emails': [(t.get(), e.get()) for t, e in self.email_entries],
                'social': [(p.get(), u.get()) for p, u in self.social_entries]
            }
            with open(filename, 'w') as f:
                json.dump(profile, f, indent=2)
            self.log_message(f"Saved: {filename}", GREEN)
    
    def load_profile(self):
        filename = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if filename:
            with open(filename) as f:
                p = json.load(f)
            self.entry_fullname.delete(0, tk.END)
            self.entry_fullname.insert(0, p.get('fullname', ''))
            self.entry_firstname.delete(0, tk.END)
            self.entry_firstname.insert(0, p.get('firstname', ''))
            self.entry_lastname.delete(0, tk.END)
            self.entry_lastname.insert(0, p.get('lastname', ''))
            self.entry_title.delete(0, tk.END)
            self.entry_title.insert(0, p.get('title', ''))
            self.entry_company.delete(0, tk.END)
            self.entry_company.insert(0, p.get('company', ''))
            self.entry_department.delete(0, tk.END)
            self.entry_department.insert(0, p.get('department', ''))
            self.text_note.delete("1.0", tk.END)
            self.text_note.insert("1.0", p.get('note', ''))
            self.entry_website.delete(0, tk.END)
            self.entry_website.insert(0, p.get('website', ''))
            self.log_message(f"Loaded: {filename}", GREEN)


if __name__ == "__main__":
    root = tk.Tk()
    app = CyberpunkNFCProgrammer(root)
    root.mainloop()
