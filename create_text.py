import os

def read_and_save_files(folder_path, output_file, extensions=None):
    """
    指定フォルダ内のファイルを読み込み、パスとその内容を出力ファイルに保存する
    
    Args:
        folder_path: 読み込むフォルダのパス
        output_file: 出力するテキストファイルのパス
        extensions: 処理する拡張子のリスト（例: ['.ts', '.tsx', '.js']）。Noneの場合はすべてのファイルを処理
    """
    # 出力ファイルを開く
    with open(output_file, 'w', encoding='utf-8') as out_f:
        # フォルダ内のファイルを走査
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                
                # Windowsスタイルのパスに変換（WSL環境の場合）
                if file_path.startswith('/mnt/c/'):
                    windows_path = 'C:' + file_path[6:].replace('/', '\\')
                else:
                    windows_path = file_path
                
                # 拡張子フィルタリング
                _, ext = os.path.splitext(file)
                if extensions and ext.lower() not in extensions:
                    continue
                
                try:
                    # ファイルを読み込む
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                    except UnicodeDecodeError:
                        # UTF-8で読めない場合はスキップ
                        continue
                    
                    # パスと内容を出力ファイルに書き込む（ご要望の形式で）
                    out_f.write(f"{windows_path}\n{content}\n\n")
                    print(f"処理: {file_path}")
                    
                except Exception as e:
                    # エラーが発生した場合はエラーメッセージを出力
                    print(f"エラー: {file_path} - {str(e)}")
    
    print(f"ファイルの内容を {output_file} に保存しました。")

# 使用例
if __name__ == "__main__":
    # WSL環境でのパス
    folder_to_read = "/mnt/c/Users/0025110396/study/chat_pj/ChatServer/scripts"  # 読み込むフォルダのパス
    output_txt_file = "scripts_output_files.txt"  # 出力ファイル名
    
    # 処理したい拡張子を指定（小文字で）
    extensions_to_process = ['.ts', '.tsx', '.js', '.jsx', '.py', '.txt', '.sh']
    
    read_and_save_files(folder_to_read, output_txt_file, extensions_to_process)
    
    # 処理完了後に確認
    if os.path.exists(output_txt_file):
        size = os.path.getsize(output_txt_file)
        print(f"出力ファイルのサイズ: {size} バイト")
        if size > 0:
            print("ファイルが正常に保存されました。")
        else:
            print("ファイルは作成されましたが、内容が空です。")
    else:
        print("出力ファイルが作成されませんでした。")