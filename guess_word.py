import pickle
import os
import msvcrt
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import time
import random
from tqdm import tqdm
from collections import defaultdict, deque
import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)

# MIN_WORD_LEN = 2
# MAX_WORD_LEN = 2

def wait_for_q():
    print("\n操作完成，按 'q' 键退出...")
    while True:
        if msvcrt.kbhit():
            key = msvcrt.getch().decode('utf-8').lower()
            if key == 'q':
                return

def is_success_button_present(driver):
    """检测分享成绩按钮是否出现"""
    try:
        # 使用更精确的选择器定位按钮，只要文本包含"分享成绩"就匹配
        share_btn = driver.find_elements(By.XPATH, "//*[contains(text(), '分享成绩')]")
        return len(share_btn) > 0
    except:
        return False

def load_word_list(file_path, word_length):
    word_set = set()
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            word = line.split()[0]
            if len(word) == word_length:
                word_set.add(word)
    return list(word_set)

def load_or_build_graph(word_list, word_length):
    graph_cache_file = f'{word_length}word_graph.pkl'
    if os.path.exists(graph_cache_file):
        print(f"加载{word_length}字词的关系图缓存...")
        with open(graph_cache_file, 'rb') as f:
            return pickle.load(f)
    else:
        print(f"构建新的{word_length}字词关系图...")
        return build_graph(word_list, word_length, graph_cache_file)

def build_graph(words, word_length, cache_file):
    graph = defaultdict(list)
    print(f"正在处理{word_length}字词（共{len(words)}个词）...")

    for i in tqdm(range(len(words)), desc=f"{word_length}字词"):
        w1 = words[i]
        for j in range(i + 1, len(words)):
            w2 = words[j]
            if one_char_diff(w1, w2):
                graph[w1].append(w2)
                graph[w2].append(w1)

    with open(cache_file, 'wb') as f:
        pickle.dump(graph, f)
    return graph

def one_char_diff(w1, w2):
    diff = 0
    for a, b in zip(w1, w2):
        if a != b:
            diff += 1
            if diff > 1:
                return False
    return diff == 1

def bfs_path(graph, start, end):
    if start == end:
        return [start]

    visited = {start: None}
    queue = deque([start])

    while queue:
        current = queue.popleft()
        for neighbor in graph.get(current, []):
            if neighbor not in visited:
                visited[neighbor] = current
                if neighbor == end:
                    path = []
                    node = end
                    while node is not None:
                        path.append(node)
                        node = visited[node]
                    return path[::-1]
                queue.append(neighbor)
    return []

def init_driver():
    options = Options()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-extensions")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--ignore-ssl-errors')
    return webdriver.Chrome(options=options)

def main():
    driver = init_driver()
    try:
        print("正在访问网站...")
        driver.get("https://xiaoce.fun/linkword")

        ActionChains(driver).move_by_offset(random.randint(10, 100), random.randint(10, 100)).perform()
        driver.execute_script(f"window.scrollBy(0, {random.randint(50, 200)});")

        wait = WebDriverWait(driver, 15)
        elements = wait.until(lambda d: d.find_elements(By.CLASS_NAME, "ant-typography"))

        source, target = "", ""
        for elem in elements:
            text = elem.text.strip()
            if "从「" in text and "到「" in text:
                parts = text.split('」')
                source = parts[0][2:]
                target = parts[1][2:]
                break

        if not source or not target:
            raise Exception("无法提取源词和目标词")

        if len(source) != len(target):
            print(f"错误：源词长度({len(source)})与目标词长度({len(target)})不一致！")
            wait_for_q()
            return

        word_length = len(target)
        print(f"任务: 从「{source}」到「{target}」（{word_length}字词）")

        print("正在加载词库...")
        word_list = load_word_list(r'hanzi-words\dict\现代汉语常用词表（草案）.txt', word_length)
        print(f"已加载 {len(word_list)} 个{word_length}字词语")

        graph = load_or_build_graph(word_list, word_length)
        print(f"关系图包含 {len(graph)} 个节点")

        path = bfs_path(graph, source, target)

        if path:
            print(f"找到路径 ({len(path) - 1}步): {' → '.join(path)}")

            for word in path[1:]:
                if is_success_button_present(driver):
                    print("检测到分享成绩按钮，猜测成功！")
                    break

                try:
                    # 检查分享成绩按钮
                    if is_success_button_present(driver):
                        break

                    # 定位输入框
                    input_box = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input.ant-input")))
                    input_box.clear()
                    for char in word:
                        input_box.send_keys(char)
                        time.sleep(random.uniform(0.05, 0.15))
                        if is_success_button_present(driver):
                            print("检测到分享成绩按钮，猜测成功！")
                            break

                    if is_success_button_present(driver):
                        break

                    input_box.send_keys("\n")
                    time.sleep(random.uniform(0.8, 1.5))
                except Exception as e:
                    print(f"输入时出错: {str(e)}")
                    driver.save_screenshot('input_error.png')
                    break

            # 最终检查是否成功
            if is_success_button_present(driver):
                print("恭喜！任务已完成！")
            else:
                print("路径输入完成")

            wait_for_q()
        else:
            print("未找到有效路径")
            wait_for_q()

    except Exception as e:
        print(f"发生错误: {str(e)}")
        driver.save_screenshot('error.png')
        wait_for_q()

if __name__ == "__main__":
    main()
    