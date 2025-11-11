#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
터미널 타이머 프로그램
실시간 카운트다운을 터미널에서 보여줍니다.
"""

import time
import sys
import os
from datetime import datetime, timedelta
import pygame
import threading
import json

class TerminalTimer:
    def __init__(self):
        self.is_running = False
        # pygame 초기화
        pygame.mixer.init()
        
        # 타이머 완료 후 알림 관련 변수
        self.reminder_active = False
        self.timer_completed_time = None
        self.reminder_thread = None
        self.reminder_lock = threading.Lock()
        
        # 현재 업무 텍스트
        self.current_task = ""
        
        # 로그 관련 변수
        self.log_dir = "logs"
        self.log_file = os.path.join(self.log_dir, "timer_log.json")
        self._ensure_log_directory()
        
        # ANSI 색상 코드
        self.COLORS = {
            'GREEN': '\033[92m',
            'RED': '\033[91m',
            'YELLOW': '\033[93m',
            'BLUE': '\033[94m',
            'MAGENTA': '\033[95m',
            'CYAN': '\033[96m',
            'WHITE': '\033[97m',
            'BOLD': '\033[1m',
            'RESET': '\033[0m'
        }
        
    def play_sound(self, sound_file):
        """MP3 파일을 재생합니다."""
        try:
            if os.path.exists(sound_file):
                pygame.mixer.music.load(sound_file)
                pygame.mixer.music.play()
                # 재생이 완료될 때까지 대기
                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)
            else:
                print(f"소리 파일을 찾을 수 없습니다: {sound_file}")
        except Exception as e:
            print(f"소리 재생 중 오류가 발생했습니다: {e}")
    
    def play_beep(self):
        """비프음을 재생합니다 (비동기적으로)."""
        try:
            if os.path.exists("voice/비프음.mp3"):
                pygame.mixer.music.load("voice/비프음.mp3")
                pygame.mixer.music.play()
        except Exception as e:
            print(f"비프음 재생 중 오류가 발생했습니다: {e}")
    
    def _ensure_log_directory(self):
        """로그 디렉토리가 없으면 생성합니다."""
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
    
    def _load_logs(self):
        """로그 파일을 로드합니다."""
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return []
        return []
    
    def _save_logs(self, logs):
        """로그를 파일에 저장합니다."""
        try:
            with open(self.log_file, 'w', encoding='utf-8') as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)
        except IOError as e:
            print(f"로그 저장 중 오류가 발생했습니다: {e}")
    
    def _get_next_log_number(self):
        """다음 로그 번호를 가져옵니다."""
        logs = self._load_logs()
        if not logs:
            return 1
        return max(log.get('number', 0) for log in logs) + 1
    
    def log_timer_start(self, total_seconds, task_description=""):
        """타이머 시작 로그를 기록합니다."""
        logs = self._load_logs()
        log_number = self._get_next_log_number()
        
        now = datetime.now()
        log_entry = {
            'number': log_number,
            'date': now.strftime('%Y년 %m월 %d일'),
            'time': now.strftime('%H시 %M분 %S초'),
            'datetime': now.isoformat(),
            'timer_duration': total_seconds,
            'timer_duration_formatted': self.format_time(total_seconds),
            'task': task_description if task_description else "(업무 없음)",
            'status': '시작',
            'completed': False
        }
        
        logs.append(log_entry)
        self._save_logs(logs)
        return log_number
    
    def log_timer_complete(self, log_number):
        """타이머 완료 로그를 업데이트합니다."""
        logs = self._load_logs()
        for log in logs:
            if log.get('number') == log_number:
                log['status'] = '완료'
                log['completed'] = True
                log['completed_datetime'] = datetime.now().isoformat()
                break
        self._save_logs(logs)
    
    def log_timer_stop(self, log_number, remaining_seconds):
        """타이머 중지 로그를 업데이트합니다."""
        logs = self._load_logs()
        for log in logs:
            if log.get('number') == log_number:
                log['status'] = '중지'
                log['completed'] = False
                log['remaining_seconds'] = remaining_seconds
                log['stopped_datetime'] = datetime.now().isoformat()
                break
        self._save_logs(logs)
    
    def start_reminder_thread(self):
        """타이머 완료 후 5분마다 알림을 재생하는 스레드를 시작합니다."""
        with self.reminder_lock:
            self.reminder_active = True
            self.timer_completed_time = time.time()
        
        def reminder_loop():
            # 5분 대기
            time.sleep(5 * 60)
            
            while True:
                with self.reminder_lock:
                    if not self.reminder_active:
                        break
                
                # 5분마다 알림 재생 (2번 반복)
                if os.path.exists("voice/타이머를다시설정해.mp3"):
                    try:
                        pygame.mixer.music.load("voice/타이머를다시설정해.mp3")
                        pygame.mixer.music.play()
                        # 재생 완료 대기
                        while pygame.mixer.music.get_busy():
                            time.sleep(0.1)
                        # 2번째 재생
                        pygame.mixer.music.play()
                        # 재생 완료 대기
                        while pygame.mixer.music.get_busy():
                            time.sleep(0.1)
                    except Exception as e:
                        print(f"알림 재생 중 오류가 발생했습니다: {e}")
                
                # 다음 알림까지 5분 대기
                time.sleep(5 * 60)
        
        self.reminder_thread = threading.Thread(target=reminder_loop, daemon=True)
        self.reminder_thread.start()
    
    def stop_reminder_thread(self):
        """알림 스레드를 중지합니다."""
        with self.reminder_lock:
            self.reminder_active = False
        if self.reminder_thread and self.reminder_thread.is_alive():
            self.reminder_thread.join(timeout=1)
    
    def play_time_notification(self, remaining_seconds, total_seconds):
        """남은 시간에 따라 알림음을 재생합니다."""
        try:
            # 50% 남았을 때 알림 (다른 알림과 겹치지 않을 때만)
            half_time = total_seconds // 2
            if remaining_seconds == half_time:
                # 다른 알림과 겹치는지 확인
                if not self.is_overlapping_with_other_notifications(remaining_seconds):
                    if os.path.exists("voice/종료50%전.mp3"):
                        pygame.mixer.music.load("voice/종료50%전.mp3")
                        pygame.mixer.music.play()
                        return
            
            # 15분 전 알림 (30분 이상 타이머에서만)
            if remaining_seconds == 15 * 60 and total_seconds >= 30 * 60:
                if os.path.exists("voice/종료15분전.mp3"):
                    pygame.mixer.music.load("voice/종료15분전.mp3")
                    pygame.mixer.music.play()
                    return
            
            # 10분 전 알림
            if remaining_seconds == 10 * 60:
                if os.path.exists("voice/종료10분전.mp3"):
                    pygame.mixer.music.load("voice/종료10분전.mp3")
                    pygame.mixer.music.play()
                    return
            
            # 5분 전 알림
            if remaining_seconds == 5 * 60:
                if os.path.exists("voice/종료5분전.mp3"):
                    pygame.mixer.music.load("voice/종료5분전.mp3")
                    pygame.mixer.music.play()
                    return
            
            # 3분 전 알림 (2번 반복)
            if remaining_seconds == 3 * 60:
                if os.path.exists("voice/종료3분전.mp3"):
                    pygame.mixer.music.load("voice/종료3분전.mp3")
                    pygame.mixer.music.play()
                    # 재생 완료 후 2번째 재생
                    while pygame.mixer.music.get_busy():
                        time.sleep(0.1)
                    pygame.mixer.music.play()
                    return
            
            # 1분 전 알림 (2번 반복)
            if remaining_seconds == 1 * 60:
                if os.path.exists("voice/종료1분전.mp3"):
                    pygame.mixer.music.load("voice/종료1분전.mp3")
                    pygame.mixer.music.play()
                    # 재생 완료 후 2번째 재생
                    while pygame.mixer.music.get_busy():
                        time.sleep(0.1)
                    pygame.mixer.music.play()
                    return
            
            # 30초 전 알림
            if remaining_seconds == 30:
                if os.path.exists("voice/종료30초전.mp3"):
                    pygame.mixer.music.load("voice/종료30초전.mp3")
                    pygame.mixer.music.play()
                    return
            
            # 10초 전 알림
            if remaining_seconds == 10:
                if os.path.exists("voice/종료10초전.mp3"):
                    pygame.mixer.music.load("voice/종료10초전.mp3")
                    pygame.mixer.music.play()
                    return
                    
        except Exception as e:
            print(f"알림음 재생 중 오류가 발생했습니다: {e}")
    
    def is_overlapping_with_other_notifications(self, remaining_seconds):
        """다른 알림과 겹치는지 확인합니다."""
        # 다른 알림 시간들과 겹치는지 확인
        notification_times = [
            15 * 60,  # 15분 전
            10 * 60,  # 10분 전
            5 * 60,   # 5분 전
            3 * 60,   # 3분 전
            1 * 60,   # 1분 전
            30,       # 30초 전
            10        # 10초 전
        ]
        
        return remaining_seconds in notification_times
    
    def clear_screen(self):
        """터미널 화면을 지웁니다."""
        os.system('clear' if os.name == 'posix' else 'cls')
        
    def format_time(self, seconds):
        """초를 시:분:초 형식으로 변환합니다."""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"
    
    def create_progress_bar(self, current, total, width=50):
        """진행률 바를 생성합니다."""
        if total == 0:
            return "█" * width
        
        progress = current / total
        filled = int(width * progress)
        bar = "█" * filled + "░" * (width - filled)
        percentage = int(progress * 100)
        
        return f"[{bar}] {percentage:3d}%"
    
    def display_timer(self, remaining_seconds, total_seconds, task_description=""):
        """타이머 화면을 표시합니다."""
        self.clear_screen()
        
        # 현재 시간
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 남은 시간
        time_str = self.format_time(remaining_seconds)
        
        # 진행률 바
        progress_bar = self.create_progress_bar(total_seconds - remaining_seconds, total_seconds)
        
        # 화면 구성
        print("=" * 60)
        print("⏰ 트레이닝 타이머")
        print("=" * 60)
        print(f"현재 시간: {current_time}")
        print()
        
        # 업무 텍스트 표시
        if task_description:
            print(f"📋 업무: {self.COLORS['CYAN']}{self.COLORS['BOLD']}{task_description}{self.COLORS['RESET']}")
            print()
        
        print(f"남은 시간: {self.COLORS['GREEN']}{self.COLORS['BOLD']}{time_str}{self.COLORS['RESET']}")
        print()
        print(f"진행률: {self.COLORS['GREEN']}{self.COLORS['BOLD']}{progress_bar}{self.COLORS['RESET']}")
        print()
        
        # 시간별 상태 메시지
        if remaining_seconds > 0:
            if remaining_seconds <= 10:
                print("🔴 마지막 10초!")
            elif remaining_seconds <= 30:
                print("🟡 마지막 30초!")
            elif remaining_seconds <= 60:
                print("🟠 마지막 1분!")
            else:
                print("🟢 타이머 진행 중...")
        else:
            print("🎉 시간 완료!")
        
        print("=" * 60)
        print("Ctrl+C를 눌러 타이머를 중지할 수 있습니다.")
    
    def countdown(self, total_seconds, task_description="", log_number=None):
        """카운트다운을 실행합니다."""
        self.is_running = True
        remaining_seconds = total_seconds
        
        try:
            while remaining_seconds > 0 and self.is_running:
                self.display_timer(remaining_seconds, total_seconds, task_description)
                
                # 시간대별 알림음 재생
                self.play_time_notification(remaining_seconds, total_seconds)
                
                # 5초 남은 순간부터 비프음 재생
                if remaining_seconds <= 5:
                    self.play_beep()
                
                time.sleep(1)
                remaining_seconds -= 1
            
            # 완료 화면
            if self.is_running:
                self.clear_screen()
                print("=" * 60)
                print("🎉 타이머 완료!")
                print("=" * 60)
                print(f"설정된 시간 {self.COLORS['GREEN']}{self.COLORS['BOLD']}{self.format_time(total_seconds)}{self.COLORS['RESET']}이 모두 경과했습니다.")
                if task_description:
                    print(f"완료한 업무: {self.COLORS['CYAN']}{self.COLORS['BOLD']}{task_description}{self.COLORS['RESET']}")
                print("=" * 60)
                
                # 완료 알림음 재생
                sound_file = "voice/타이머종료.mp3"
                print("🔊 완료 알림음을 재생합니다...")
                self.play_sound(sound_file)
                
                # 로그 업데이트
                if log_number:
                    self.log_timer_complete(log_number)
                
                # 5분 후부터 5분마다 알림 재생 스레드 시작
                self.start_reminder_thread()
                
        except KeyboardInterrupt:
            self.is_running = False
            self.clear_screen()
            print("=" * 60)
            print("⏹️ 타이머가 중지되었습니다.")
            print(f"남은 시간: {self.COLORS['GREEN']}{self.COLORS['BOLD']}{self.format_time(remaining_seconds)}{self.COLORS['RESET']}")
            if task_description:
                print(f"진행 중이던 업무: {self.COLORS['CYAN']}{self.COLORS['BOLD']}{task_description}{self.COLORS['RESET']}")
            print("=" * 60)
            
            # 로그 업데이트
            if log_number:
                self.log_timer_stop(log_number, remaining_seconds)
    
    def get_user_input(self):
        """사용자로부터 시간 입력을 받습니다."""
        # 사용자가 타이머를 설정하기 시작하면 알림 중지
        self.stop_reminder_thread()
        
        print("=" * 60)
        print("⏰ 트레이닝 타이머")
        print("=" * 60)
        print("시간을 선택해주세요:")
        print()
        print("단축키:")
        print("  1️⃣  30분") 
        print("  2️⃣  20분")
        print("  3️⃣  15분")
        print("  4️⃣  10분")
        print("  5️⃣  직접입력")
        print()
        print("=" * 60)
        
        total_seconds = None
        while True:
            try:
                user_input = input("선택 (1-5): ").strip()
                
                if not user_input:
                    print("번호를 입력해주세요!")
                    continue
                
                # 단축키 처리
                if user_input == "1":
                    total_seconds = 30 * 60  # 30분
                    break
                elif user_input == "2":
                    total_seconds = 20 * 60  # 20분
                    break
                elif user_input == "3":
                    total_seconds = 15 * 60  # 15분
                    break
                elif user_input == "4":
                    total_seconds = 10 * 60  # 10분
                    break
                elif user_input == "5":
                    total_seconds = self.get_custom_input()
                    break
                else:
                    print("1-5 중에서 선택해주세요!")
                    continue
                
            except KeyboardInterrupt:
                print("\n프로그램을 종료합니다.")
                sys.exit(0)
        
        # 업무 텍스트 입력 받기
        print("\n" + "=" * 60)
        print("📋 이 시간 동안 할 업무를 입력해주세요:")
        print("=" * 60)
        print("(엔터만 누르면 업무 없이 진행됩니다)")
        print("=" * 60)
        
        try:
            task_description = input("\n업무 입력: ").strip()
            self.current_task = task_description
            return total_seconds, task_description
        except KeyboardInterrupt:
            print("\n프로그램을 종료합니다.")
            sys.exit(0)
    
    def get_custom_input(self):
        """직접 시간 입력을 받습니다."""
        print("\n" + "=" * 60)
        print("⏰ 직접 시간 입력")
        print("=" * 60)
        print("시간을 입력해주세요:")
        print("예시:")
        print("  - 5분: 5m 또는 300")
        print("  - 1시간 30분: 1h30m 또는 5400")
        print("  - 2시간: 2h 또는 7200")
        print("  - 30초: 30s 또는 30")
        print("=" * 60)
        
        while True:
            try:
                user_input = input("시간 입력: ").strip().lower()
                
                if not user_input:
                    print("시간을 입력해주세요!")
                    continue
                
                # 시간 파싱
                total_seconds = self.parse_time_input(user_input)
                
                if total_seconds <= 0:
                    print("0보다 큰 시간을 입력해주세요!")
                    continue
                
                return total_seconds
                
            except ValueError:
                print("올바른 시간 형식을 입력해주세요!")
            except KeyboardInterrupt:
                print("\n프로그램을 종료합니다.")
                sys.exit(0)
    
    def parse_time_input(self, time_str):
        """시간 문자열을 초로 변환합니다."""
        # 숫자만 입력된 경우 (초로 간주)
        if time_str.isdigit():
            return int(time_str)
        
        total_seconds = 0
        
        # 시간 단위 파싱
        if 'h' in time_str:
            parts = time_str.split('h')
            if len(parts) == 2:
                hours = int(parts[0]) if parts[0] else 0
                total_seconds += hours * 3600
                time_str = parts[1]
        
        if 'm' in time_str:
            parts = time_str.split('m')
            if len(parts) == 2:
                minutes = int(parts[0]) if parts[0] else 0
                total_seconds += minutes * 60
                time_str = parts[1]
        
        if 's' in time_str:
            parts = time_str.split('s')
            if len(parts) == 2:
                seconds = int(parts[0]) if parts[0] else 0
                total_seconds += seconds
                time_str = parts[1]
        
        # 남은 숫자가 있으면 초로 추가
        if time_str.strip().isdigit():
            total_seconds += int(time_str.strip())
        
        return total_seconds

def main():
    """메인 함수"""
    timer = TerminalTimer()
    
    try:
        while True:
            # 사용자 입력 받기 (시간과 업무)
            total_seconds, task_description = timer.get_user_input()
            
            # 타이머 시작 로그 기록
            log_number = timer.log_timer_start(total_seconds, task_description)
            
            # 타이머 시작
            print(f"\n타이머를 {timer.format_time(total_seconds)}로 설정했습니다.")
            if task_description:
                print(f"업무: {task_description}")
            print(f"📝 로그 번호: {log_number}")
            print("3초 후 시작됩니다...")
            
            for i in range(3, 0, -1):
                print(f"{i}...")
                timer.play_beep()  # 비프음 재생
                time.sleep(1)
            
            # 카운트다운 실행
            timer.countdown(total_seconds, task_description, log_number)
            
            # 타이머 완료 후 다시 시작할지 물어보기
            print("\n" + "=" * 60)
            print("다시 타이머를 시작하시겠습니까?")
            print("=" * 60)
            print("  Enter: 다시 시작")
            print("  Ctrl+C: 프로그램 종료")
            print("=" * 60)
            
            # 잠시 대기 (사용자가 Enter를 누르거나 Ctrl+C를 누를 수 있도록)
            try:
                input("\n계속하려면 Enter를 누르세요...")
            except KeyboardInterrupt:
                print("\n프로그램을 종료합니다.")
                sys.exit(0)
            
            # 화면을 지우고 다시 시작
            timer.clear_screen()
        
    except KeyboardInterrupt:
        print("\n프로그램을 종료합니다.")
        sys.exit(0)
    except Exception as e:
        print(f"오류가 발생했습니다: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
