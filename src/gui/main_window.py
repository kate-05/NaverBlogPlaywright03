"""
GUI 메인 윈도우
Tkinter 기반 인터페이스
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from pathlib import Path
from datetime import datetime
from typing import Tuple
import threading
import sys
import os
import io
import queue

# 프로젝트 루트를 path에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.crawler.batch_crawler import crawl_multiple_blog_ids, resume_crawling
from src.utils.checkpoint_manager import CheckpointManager


class StdoutRedirector:
    """표준 출력 리다이렉터 - GUI 로그로 전달"""
    def __init__(self, log_callback, queue_obj):
        self.log_callback = log_callback
        self.queue = queue_obj
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
    
    def write(self, text):
        """출력 텍스트를 큐에 추가"""
        if text.strip():  # 빈 줄 제외
            self.queue.put(text)
            # 원본 출력도 유지 (디버깅용)
            try:
                self.original_stdout.write(text)
                self.original_stdout.flush()
            except:
                pass
    
    def flush(self):
        """플러시 (필요 시 원본 출력 플러시)"""
        try:
            self.original_stdout.flush()
        except:
            pass
    
    def restore(self):
        """원본 출력 복원"""
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr


class MainWindow:
    """메인 윈도우 클래스"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("네이버 블로그 크롤러")
        self.root.geometry("900x700")
        self.root.minsize(800, 600)
        
        # 상태 변수
        self.stop_requested = False
        self.is_crawling = False
        self.checkpoint_manager = CheckpointManager()
        
        # 설정 변수
        self.save_interval = 10
        
        # 표준 출력 리다이렉션 관련
        self.stdout_redirector = None
        self.log_queue = None
        
        # 화면 초기화
        self.show_main_screen()
    
    def show_main_screen(self):
        """메인 화면 표시"""
        # 기존 위젯 제거
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # 메뉴바
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="파일", menu=file_menu)
        file_menu.add_command(label="종료", command=self.root.quit)
        
        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="설정", menu=settings_menu)
        settings_menu.add_command(label="설정 변경", command=self.show_settings_dialog)
        
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="도움말", menu=help_menu)
        help_menu.add_command(label="사용 방법", command=self.show_help)
        
        # 메인 프레임
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 입력 방법 선택
        input_frame = ttk.LabelFrame(main_frame, text="입력 방법 선택", padding="10")
        input_frame.pack(fill=tk.X, pady=5)
        
        self.input_method = tk.StringVar(value="single")
        ttk.Radiobutton(input_frame, text="단일 블로그 ID 입력", 
                       variable=self.input_method, value="single",
                       command=self.on_input_method_change).pack(anchor=tk.W)
        
        self.blog_id_entry = ttk.Entry(input_frame, width=50)
        self.blog_id_entry.pack(fill=tk.X, pady=5)
        
        ttk.Label(input_frame, text="또는").pack(anchor=tk.W, pady=5)
        
        ttk.Radiobutton(input_frame, text="파일로 여러 블로그 ID 업로드",
                       variable=self.input_method, value="file",
                       command=self.on_input_method_change).pack(anchor=tk.W)
        
        file_frame = ttk.Frame(input_frame)
        file_frame.pack(fill=tk.X, pady=5)
        
        self.file_path_var = tk.StringVar()
        self.file_path_entry = ttk.Entry(file_frame, textvariable=self.file_path_var, 
                                         state='readonly', width=40)
        self.file_path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        ttk.Button(file_frame, text="찾기", command=self.select_file).pack(side=tk.RIGHT)
        
        # 재개 옵션
        resume_frame = ttk.LabelFrame(main_frame, text="재개 옵션", padding="10")
        resume_frame.pack(fill=tk.X, pady=5)
        
        self.resume_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(resume_frame, text="중단된 크롤링 재개",
                       variable=self.resume_var,
                       command=self.on_resume_check).pack(anchor=tk.W)
        
        checkpoint_frame = ttk.Frame(resume_frame)
        checkpoint_frame.pack(fill=tk.X, pady=5)
        
        self.checkpoint_path_var = tk.StringVar()
        self.checkpoint_path_entry = ttk.Entry(checkpoint_frame, 
                                               textvariable=self.checkpoint_path_var,
                                               state='readonly', width=40)
        self.checkpoint_path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        ttk.Button(checkpoint_frame, text="찾기", 
                  command=self.select_checkpoint_file).pack(side=tk.RIGHT)
        
        # 설정 요약
        settings_summary_frame = ttk.LabelFrame(main_frame, text="현재 설정 요약", padding="10")
        settings_summary_frame.pack(fill=tk.X, pady=5)
        
        self.settings_label = ttk.Label(settings_summary_frame, 
                                        text=f"• 저장 간격: {self.save_interval}개 포스트마다\n"
                                             f"• 파일 분할: 사용 안 함\n"
                                             f"• 출력 형식: JSON")
        self.settings_label.pack(anchor=tk.W)
        
        ttk.Button(settings_summary_frame, text="설정 변경", 
                  command=self.show_settings_dialog).pack(anchor=tk.E, pady=5)
        
        # 버튼 영역
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(button_frame, text="크롤링 시작", 
                  command=self.start_crawling).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="설정", 
                  command=self.show_settings_dialog).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="도움말", 
                  command=self.show_help).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="종료", 
                  command=self.root.quit).pack(side=tk.RIGHT, padx=5)
        
        # 상태 표시줄
        self.status_bar = ttk.Label(main_frame, text="준비", relief=tk.SUNKEN)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM, pady=5)
        
        # 초기 상태 설정
        self.on_input_method_change()
        self.on_resume_check()
    
    def on_input_method_change(self):
        """입력 방법 변경 이벤트"""
        if self.input_method.get() == "single":
            self.blog_id_entry.config(state='normal')
        else:
            self.blog_id_entry.config(state='disabled')
    
    def on_resume_check(self):
        """재개 옵션 체크 이벤트"""
        if self.resume_var.get():
            self.blog_id_entry.config(state='disabled')
            self.file_path_var.set("")
        else:
            if self.input_method.get() == "single":
                self.blog_id_entry.config(state='normal')
    
    def select_file(self):
        """파일 선택"""
        filename = filedialog.askopenfilename(
            title="블로그 ID 파일 선택",
            filetypes=[("텍스트 파일", "*.txt"), ("CSV 파일", "*.csv"), ("모든 파일", "*.*")]
        )
        if filename:
            self.file_path_var.set(filename)
    
    def select_checkpoint_file(self):
        """체크포인트 파일 선택"""
        filename = filedialog.askopenfilename(
            title="체크포인트 파일 선택",
            initialdir="checkpoints",
            filetypes=[("JSON 파일", "*.json"), ("모든 파일", "*.*")]
        )
        if filename:
            self.checkpoint_path_var.set(filename)
    
    def show_settings_dialog(self):
        """설정 대화상자"""
        dialog = tk.Toplevel(self.root)
        dialog.title("설정")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="저장 간격 (포스트 수):").pack(anchor=tk.W, padx=10, pady=5)
        
        save_interval_var = tk.IntVar(value=self.save_interval)
        spinbox = ttk.Spinbox(dialog, from_=1, to=100, textvariable=save_interval_var, width=10)
        spinbox.pack(anchor=tk.W, padx=10, pady=5)
        
        def save_settings():
            self.save_interval = save_interval_var.get()
            self.settings_label.config(
                text=f"• 저장 간격: {self.save_interval}개 포스트마다\n"
                     f"• 파일 분할: 사용 안 함\n"
                     f"• 출력 형식: JSON"
            )
            dialog.destroy()
        
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(button_frame, text="저장", command=save_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="취소", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    def show_help(self):
        """도움말 표시"""
        help_text = """
네이버 블로그 크롤러 사용 방법

1. 입력 방법 선택
   - 단일 블로그 ID: 하나의 블로그 ID를 직접 입력
   - 파일 업로드: 여러 블로그 ID가 있는 텍스트 파일 선택
     (한 줄에 하나의 블로그 ID)

2. 크롤링 시작
   - "크롤링 시작" 버튼 클릭
   - 진행 상황 화면에서 실시간으로 진행 상황 확인

3. 중단 및 재개
   - "중단" 버튼으로 크롤링 중단 가능
   - 중단된 크롤링은 "재개 옵션"으로 계속 진행 가능

4. 결과 확인
   - 크롤링 완료 후 결과 파일 경로 확인
   - "폴더 열기" 버튼으로 결과 파일 위치 열기
        """
        messagebox.showinfo("도움말", help_text)
    
    def validate_inputs(self) -> Tuple[bool, str]:
        """입력값 검증"""
        if self.resume_var.get():
            if not self.checkpoint_path_var.get():
                return False, "체크포인트 파일을 선택해주세요."
            if not Path(self.checkpoint_path_var.get()).exists():
                return False, "체크포인트 파일이 존재하지 않습니다."
        else:
            if self.input_method.get() == "single":
                blog_id = self.blog_id_entry.get().strip()
                if not blog_id:
                    return False, "블로그 ID를 입력해주세요."
            else:
                file_path = self.file_path_var.get()
                if not file_path:
                    return False, "파일을 선택해주세요."
                if not Path(file_path).exists():
                    return False, "파일이 존재하지 않습니다."
        
        return True, ""
    
    def load_blog_ids_from_file(self, file_path: str) -> list:
        """파일에서 블로그 ID 로드"""
        blog_ids = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                blog_id = line.strip()
                if blog_id:
                    blog_ids.append(blog_id)
        return blog_ids
    
    def start_crawling(self):
        """크롤링 시작"""
        # 입력 검증
        is_valid, error_msg = self.validate_inputs()
        if not is_valid:
            messagebox.showerror("오류", error_msg)
            return
        
        # 크롤링 상태 플래그 설정
        self.is_crawling = True
        self.stop_requested = False
        
        # 위젯 변수를 미리 읽어서 저장 (스레드 안전을 위해)
        self.crawl_params = {
            'resume_mode': self.resume_var.get(),
            'blog_ids': [],
            'checkpoint_path': ''
        }
        
        if self.crawl_params['resume_mode']:
            self.crawl_params['checkpoint_path'] = self.checkpoint_path_var.get()
        else:
            if self.input_method.get() == "single":
                blog_id = self.blog_id_entry.get().strip()
                if blog_id:
                    self.crawl_params['blog_ids'] = [blog_id]
            else:
                file_path = self.file_path_var.get()
                if file_path:
                    self.crawl_params['blog_ids'] = self.load_blog_ids_from_file(file_path)
        
        # 진행 상황 화면으로 전환
        self.show_progress_screen()
    
    def show_progress_screen(self):
        """진행 상황 화면"""
        # 기존 위젯 제거
        for widget in self.root.winfo_children():
            widget.destroy()
        
        self.stop_requested = False
        # is_crawling은 start_crawling에서 이미 설정됨
        
        # 메뉴바
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # 진행률 표시
        progress_frame = ttk.LabelFrame(self.root, text="전체 진행 상황", padding="10")
        progress_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, 
                                           maximum=100, length=400)
        self.progress_bar.pack(fill=tk.X, pady=5)
        
        self.progress_label = ttk.Label(progress_frame, text="0% (0/0)")
        self.progress_label.pack(pady=5)
        
        # 로그 영역
        log_frame = ttk.LabelFrame(self.root, text="로그", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=20, width=80)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # 버튼 영역
        button_frame = ttk.Frame(self.root)
        button_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(button_frame, text="중단", 
                  command=self.confirm_stop).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="메인으로", 
                  command=self.show_main_screen).pack(side=tk.RIGHT, padx=5)
        
        # 상태 표시줄
        self.status_bar = ttk.Label(self.root, text="크롤링 진행 중...", relief=tk.SUNKEN)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM, pady=5)
        
        # 크롤링 스레드 시작
        threading.Thread(target=self.crawl_worker, daemon=True).start()
    
    def log_message(self, message: str, error: bool = False):
        """로그 메시지 추가 (스레드 안전)"""
        def _log():
            try:
                if hasattr(self, 'log_text') and self.log_text.winfo_exists():
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    log_msg = f"[{timestamp}] {message}\n"
                    
                    self.log_text.insert(tk.END, log_msg)
                    if error:
                        start_pos = self.log_text.index(f"end-{len(log_msg)}c")
                        end_pos = self.log_text.index(tk.END)
                        self.log_text.tag_add("error", start_pos, end_pos)
                        self.log_text.tag_config("error", foreground="red")
                    
                    self.log_text.see(tk.END)
            except Exception:
                pass  # 위젯이 파괴된 경우 무시
        
        # 메인 스레드에서 실행
        self.root.after(0, _log)
    
    def update_progress(self, current: int, total: int):
        """진행률 업데이트 (스레드 안전)"""
        def _update():
            try:
                if hasattr(self, 'progress_var') and hasattr(self, 'progress_label'):
                    if hasattr(self, 'progress_label') and hasattr(self.progress_label, 'winfo_exists'):
                        if self.progress_label.winfo_exists():
                            if total > 0:
                                progress = (current / total) * 100
                                if hasattr(self, 'progress_var'):
                                    self.progress_var.set(progress)
                                self.progress_label.config(text=f"{progress:.1f}% ({current}/{total})")
            except Exception:
                pass  # 위젯이 파괴된 경우 무시
        
        # 메인 스레드에서 실행
        self.root.after(0, _update)
    
    def confirm_stop(self):
        """중단 확인"""
        if messagebox.askyesno("크롤링 중단", 
                              "크롤링을 중단하시겠습니까?\n진행 중인 작업은 저장됩니다."):
            self.stop_requested = True
            self.log_message("사용자가 크롤링 중단을 요청했습니다.", False)
    
    def should_stop(self) -> bool:
        """중단 확인 콜백"""
        return self.stop_requested
    
    def setup_stdout_redirect(self):
        """표준 출력 리다이렉션 설정"""
        if self.log_queue is None:
            self.log_queue = queue.Queue()
        
        # 표준 출력 리다이렉터 생성
        self.stdout_redirector = StdoutRedirector(self.log_message, self.log_queue)
        sys.stdout = self.stdout_redirector
        sys.stderr = self.stdout_redirector
        
        # 큐에서 로그 읽기 시작
        self.root.after(100, self.process_log_queue)
    
    def restore_stdout(self):
        """표준 출력 복원"""
        if self.stdout_redirector:
            self.stdout_redirector.restore()
            self.stdout_redirector = None
    
    def process_log_queue(self):
        """로그 큐에서 메시지 읽어서 GUI에 표시"""
        try:
            while True:
                try:
                    message = self.log_queue.get_nowait()
                    # 줄바꿈 제거하고 log_message로 전달
                    message = message.rstrip('\n\r')
                    if message:
                        self.log_message(message, error=False)
                except queue.Empty:
                    break
        except Exception:
            pass
        
        # 계속 체크 (크롤링 중일 때만)
        if self.is_crawling:
            self.root.after(100, self.process_log_queue)
    
    def crawl_worker(self):
        """크롤링 워커 스레드"""
        try:
            # 표준 출력 리다이렉션 설정
            self.setup_stdout_redirect()
            
            # 미리 읽은 파라미터 사용 (스레드 안전)
            params = getattr(self, 'crawl_params', {})
            resume_mode = params.get('resume_mode', False)
            blog_ids = params.get('blog_ids', [])
            checkpoint_path = params.get('checkpoint_path', '')
            
            # 크롤링 시작
            if resume_mode:
                # 재개 모드
                output_path = f"output/crawl_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                
                self.log_message("체크포인트에서 크롤링 재개 중...")
                new_posts = resume_crawling(
                    checkpoint_path,
                    output_path,
                    self.checkpoint_manager,
                    delay=0.5,
                    timeout=30,
                    should_stop=self.should_stop,
                    save_interval=self.save_interval
                )
                total_blogs = 0
            else:
                # 새로 시작
                if not blog_ids:
                    self.log_message("블로그 ID를 입력해주세요.", True)
                    self.root.after(0, self.show_main_screen)
                    return
                
                output_path = f"output/crawl_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                
                self.log_message(f"크롤링 시작: {len(blog_ids)}개 블로그")
                
                crawl_multiple_blog_ids(
                    blog_ids,
                    output_path,
                    self.checkpoint_manager,
                    delay=0.5,
                    timeout=30,
                    should_stop=self.should_stop,
                    save_interval=self.save_interval
                )
                total_blogs = len(blog_ids)
            
            self.log_message("크롤링 완료!")
            # 메인 스레드에서 결과 화면 표시
            self.root.after(0, lambda: self.show_result_screen(output_path, total_blogs))
            
        except Exception as e:
            import traceback
            error_msg = str(e)
            traceback.print_exc()
            self.log_message(f"오류 발생: {error_msg}", True)
            # 메인 스레드에서 에러 다이얼로그 표시
            self.root.after(0, lambda: messagebox.showerror("오류", f"크롤링 중 오류가 발생했습니다:\n{error_msg}"))
            self.root.after(0, self.show_main_screen)
        finally:
            # 크롤링 상태 플래그 해제
            self.is_crawling = False
            # 표준 출력 복원
            self.restore_stdout()
    
    def show_result_screen(self, output_path: str, total_blogs: int):
        """결과 화면"""
        # 기존 위젯 제거
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # 메뉴바
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # 결과 요약
        result_frame = ttk.LabelFrame(self.root, text="크롤링 결과 요약", padding="10")
        result_frame.pack(fill=tk.X, padx=10, pady=5)
        
        success_label = ttk.Label(result_frame, text="✓ 크롤링이 성공적으로 완료되었습니다!")
        success_label.pack(anchor=tk.W, pady=5)
        
        ttk.Label(result_frame, text=f"• 출력 파일: {Path(output_path).name}").pack(anchor=tk.W)
        
        # 결과 파일 영역
        file_frame = ttk.LabelFrame(self.root, text="결과 파일", padding="10")
        file_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(file_frame, text=f"파일: {output_path}").pack(anchor=tk.W, pady=5)
        
        def open_folder():
            folder = Path(output_path).parent
            os.startfile(folder)
        
        ttk.Button(file_frame, text="폴더 열기", command=open_folder).pack(anchor=tk.W, pady=5)
        
        # 버튼 영역
        button_frame = ttk.Frame(self.root)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(button_frame, text="다시 크롤링", 
                  command=self.show_main_screen).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="종료", 
                  command=self.root.quit).pack(side=tk.RIGHT, padx=5)
        
        # 상태 표시줄
        self.status_bar = ttk.Label(self.root, text="크롤링 완료", relief=tk.SUNKEN)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM, pady=5)
        
        self.stop_requested = False
        self.is_crawling = False


def main():
    """메인 함수"""
    root = tk.Tk()
    app = MainWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()

