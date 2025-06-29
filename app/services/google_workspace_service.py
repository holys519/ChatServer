"""
Google Workspace連携サービス
医療従事者の学会発表資料作成を支援
"""
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
import asyncio

class GoogleWorkspaceService:
    """Google Workspace連携サービス"""
    
    def __init__(self):
        self.slide_templates = {
            "case_report": {
                "title": "症例報告テンプレート",
                "slides": [
                    {"title": "タイトルスライド", "content": ["演題名", "発表者", "所属", "日付"]},
                    {"title": "背景・目的", "content": ["疾患の概要", "症例の特殊性", "報告の意義"]},
                    {"title": "症例", "content": ["患者基本情報", "主訴・現病歴", "既往歴・家族歴"]},
                    {"title": "検査所見", "content": ["血液検査", "画像検査", "特殊検査"]},
                    {"title": "診断・治療", "content": ["診断根拠", "治療方針", "治療経過"]},
                    {"title": "考察", "content": ["文献的考察", "本症例の特徴", "臨床的意義"]},
                    {"title": "結語", "content": ["要点のまとめ", "今後の課題"]},
                    {"title": "参考文献", "content": ["主要文献リスト"]}
                ]
            },
            "research_presentation": {
                "title": "研究発表テンプレート",
                "slides": [
                    {"title": "タイトルスライド", "content": ["研究タイトル", "研究者", "所属機関"]},
                    {"title": "背景・目的", "content": ["研究背景", "問題設定", "研究目的・仮説"]},
                    {"title": "方法", "content": ["研究デザイン", "対象・期間", "評価項目・統計手法"]},
                    {"title": "結果", "content": ["対象背景", "主要評価項目", "副次評価項目"]},
                    {"title": "考察", "content": ["結果の解釈", "先行研究との比較", "研究の限界"]},
                    {"title": "結論", "content": ["主要な知見", "臨床的意義", "今後の展望"]},
                    {"title": "参考文献", "content": ["重要文献"]}
                ]
            },
            "literature_review": {
                "title": "文献レビューテンプレート",
                "slides": [
                    {"title": "タイトルスライド", "content": ["レビュータイトル", "発表者", "所属"]},
                    {"title": "目的・方法", "content": ["レビューの目的", "検索戦略", "選択基準"]},
                    {"title": "文献概観", "content": ["検索結果", "文献の特徴", "エビデンスレベル"]},
                    {"title": "主要知見", "content": ["診断に関する知見", "治療に関する知見", "予後に関する知見"]},
                    {"title": "エビデンス統合", "content": ["一致した知見", "相反する結果", "ギャップの特定"]},
                    {"title": "臨床への示唆", "content": ["実臨床への応用", "推奨事項", "注意点"]},
                    {"title": "今後の課題", "content": ["研究ギャップ", "必要な研究", "方法論的改善点"]}
                ]
            }
        }
        
        self.medical_style_guide = {
            "fonts": {
                "title": "Arial, 32pt, Bold",
                "heading": "Arial, 24pt, Bold", 
                "body": "Arial, 18pt, Regular",
                "caption": "Arial, 14pt, Regular"
            },
            "colors": {
                "primary": "#1f4e79",  # 医療ブルー
                "secondary": "#2e8b57", # メディカルグリーン
                "accent": "#cd853f",   # ゴールド
                "text": "#2c2c2c",    # ダークグレー
                "background": "#ffffff" # ホワイト
            },
            "layout": {
                "title_position": "center",
                "content_margin": "10%",
                "image_size": "medium",
                "bullet_style": "professional"
            }
        }
    
    async def generate_presentation_slides(self, content_data: Dict[str, Any]) -> Dict[str, Any]:
        """発表スライドデータ生成"""
        presentation_type = content_data.get("type", "case_report")
        topic = content_data.get("topic", "")
        supporting_data = content_data.get("supporting_literature", [])
        
        template = self.slide_templates.get(presentation_type, self.slide_templates["case_report"])
        
        # スライド内容の生成
        slides = []
        for slide_template in template["slides"]:
            slide_content = await self._generate_slide_content(
                slide_template, topic, supporting_data, presentation_type
            )
            slides.append(slide_content)
        
        # Google Slides形式のデータ構造
        presentation_data = {
            "title": f"{topic} - {template['title']}",
            "slides": slides,
            "style": self.medical_style_guide,
            "export_formats": ["google_slides", "powerpoint", "pdf"],
            "metadata": {
                "created_date": datetime.now().isoformat(),
                "template_type": presentation_type,
                "slide_count": len(slides)
            }
        }
        
        return presentation_data
    
    async def _generate_slide_content(self, slide_template: Dict, topic: str, 
                                    supporting_data: List[Dict], presentation_type: str) -> Dict[str, Any]:
        """個別スライドの内容生成"""
        slide_title = slide_template["title"]
        content_areas = slide_template["content"]
        
        slide = {
            "title": slide_title,
            "layout": "title_and_content",
            "elements": []
        }
        
        # タイトルスライドの特別処理
        if slide_title == "タイトルスライド":
            slide["elements"] = [
                {"type": "title", "text": topic, "style": "title"},
                {"type": "subtitle", "text": f"発表者: [発表者名]\n所属: [所属機関]\n日付: {datetime.now().strftime('%Y年%m月%d日')}", "style": "subtitle"}
            ]
        
        # 参考文献スライドの特別処理
        elif slide_title == "参考文献":
            references = self._format_references(supporting_data[:10])  # 最大10文献
            slide["elements"] = [
                {"type": "title", "text": "参考文献", "style": "heading"},
                {"type": "text", "text": references, "style": "body"}
            ]
        
        # その他のスライド
        else:
            slide["elements"].append({"type": "title", "text": slide_title, "style": "heading"})
            
            # 内容エリアごとに要素を生成
            for area in content_areas:
                content = await self._generate_content_for_area(area, topic, supporting_data)
                slide["elements"].append({
                    "type": "bullet_list",
                    "items": content,
                    "style": "body"
                })
        
        return slide
    
    async def _generate_content_for_area(self, area: str, topic: str, supporting_data: List[Dict]) -> List[str]:
        """コンテンツエリアの具体的内容生成"""
        # 各エリアに応じた内容生成ロジック
        content_generators = {
            "疾患の概要": lambda: [
                f"{topic}の定義と特徴",
                "疫学的データ（有病率・発症率）",
                "病態生理学的メカニズム"
            ],
            "症例の特殊性": lambda: [
                "本症例の特徴的な点",
                "典型例との相違点",
                "診断上の困難さ"
            ],
            "診断根拠": lambda: [
                "主要症状・身体所見",
                "検査所見の解釈",
                "鑑別診断の除外過程"
            ],
            "文献的考察": lambda: self._generate_literature_discussion(supporting_data),
            "研究背景": lambda: [
                "現在の知見の整理",
                "未解決の課題",
                "本研究の着想"
            ],
            "研究デザイン": lambda: [
                "研究デザインの選択理由",
                "バイアス制御の方法",
                "倫理的配慮"
            ]
        }
        
        generator = content_generators.get(area)
        if generator:
            return generator()
        else:
            # デフォルトの汎用コンテンツ
            return [
                f"{area}に関する要点1",
                f"{area}に関する要点2", 
                f"{area}に関する要点3"
            ]
    
    def _generate_literature_discussion(self, supporting_data: List[Dict]) -> List[str]:
        """文献的考察の生成"""
        if not supporting_data:
            return ["関連文献の検討が必要", "先行研究との比較", "本症例の位置づけ"]
        
        discussion_points = []
        
        # 高エビデンス文献の考察
        high_evidence = [p for p in supporting_data if p.get("evidence_level") in ["1a", "1b"]]
        if high_evidence:
            discussion_points.append(f"高品質なエビデンス（{len(high_evidence)}報）では...")
        
        # 最近の知見
        recent_studies = [p for p in supporting_data if self._is_recent_study(p)]
        if recent_studies:
            discussion_points.append(f"最近の研究（{len(recent_studies)}報）により明らかになった点")
        
        # 相反する結果があれば
        discussion_points.append("先行研究との一致点・相違点")
        discussion_points.append("本症例が文献的知見に与える意義")
        
        return discussion_points
    
    def _is_recent_study(self, paper: Dict) -> bool:
        """最近の研究かどうか判定"""
        pub_date = paper.get("publication_date")
        if not pub_date:
            return False
        
        try:
            pub_year = int(pub_date.split("-")[0])
            current_year = datetime.now().year
            return current_year - pub_year <= 3
        except:
            return False
    
    def _format_references(self, papers: List[Dict]) -> str:
        """参考文献の形式化"""
        references = []
        
        for i, paper in enumerate(papers, 1):
            authors = paper.get("authors", ["Unknown"])
            title = paper.get("title", "No title")
            journal = paper.get("journal", "Unknown journal")
            year = paper.get("publication_date", "").split("-")[0] if paper.get("publication_date") else "Unknown"
            
            # 著者名の整理（最初の3名 + et al.）
            if len(authors) > 3:
                author_str = f"{', '.join(authors[:3])}, et al."
            else:
                author_str = ', '.join(authors)
            
            reference = f"{i}. {author_str} {title} {journal}. {year}."
            references.append(reference)
        
        return '\n'.join(references)
    
    async def generate_abstract_document(self, content_data: Dict[str, Any]) -> Dict[str, Any]:
        """抄録文書の生成"""
        abstract_type = content_data.get("type", "case_report")
        topic = content_data.get("topic", "")
        key_findings = content_data.get("key_findings", [])
        
        # 抄録構造の定義
        abstract_structure = {
            "case_report": {
                "sections": ["背景", "症例", "結果", "結論"],
                "word_limits": {"背景": 100, "症例": 150, "結果": 100, "結論": 50}
            },
            "research": {
                "sections": ["目的", "方法", "結果", "結論"],
                "word_limits": {"目的": 80, "方法": 120, "結果": 120, "結論": 80}
            }
        }
        
        structure = abstract_structure.get(abstract_type, abstract_structure["case_report"])
        
        abstract_document = {
            "title": topic,
            "type": abstract_type,
            "sections": {},
            "metadata": {
                "created_date": datetime.now().isoformat(),
                "target_conference": "[学会名]",
                "presentation_type": "[口演/ポスター]"
            }
        }
        
        # 各セクションの内容生成
        for section in structure["sections"]:
            word_limit = structure["word_limits"].get(section, 100)
            content = await self._generate_abstract_section(section, topic, key_findings, word_limit)
            abstract_document["sections"][section] = {
                "content": content,
                "word_count": len(content),
                "word_limit": word_limit
            }
        
        return abstract_document
    
    async def _generate_abstract_section(self, section: str, topic: str, 
                                       key_findings: List[str], word_limit: int) -> str:
        """抄録セクションの内容生成"""
        section_templates = {
            "背景": f"{topic}について、[背景となる医学的知見]。本症例では[特殊性や意義]について報告する。",
            "目的": f"{topic}に関して、[研究目的や仮説]を明らかにすることを目的とした。",
            "症例": "[年齢・性別]の患者。主訴は[主訴]。[診断過程や治療経過の要約]。",
            "方法": "[研究デザイン]を用いて、[対象・期間・評価項目]について検討した。",
            "結果": "[主要な結果・所見]。[数値データがあれば具体的に]。",
            "結論": f"{topic}において、[主要な知見や臨床的意義]が示された。"
        }
        
        template = section_templates.get(section, f"[{section}の内容]")
        
        # キーファインディングスがあれば反映
        if key_findings and section in ["結果", "結論"]:
            findings_text = "、".join(key_findings[:2])  # 主要な2つの知見
            template = template.replace("[主要な結果・所見]", findings_text)
            template = template.replace("[主要な知見や臨床的意義]", findings_text)
        
        return template
    
    async def export_to_google_workspace(self, document_data: Dict[str, Any], 
                                       export_type: str = "slides") -> Dict[str, str]:
        """Google Workspace形式でのエクスポート"""
        # 実際のGoogle Slides/Docs APIとの連携は今後実装
        # 現在はエクスポート用データの準備
        
        export_urls = {
            "slides": "https://docs.google.com/presentation/d/[PRESENTATION_ID]/edit",
            "docs": "https://docs.google.com/document/d/[DOCUMENT_ID]/edit",
            "sheets": "https://docs.google.com/spreadsheets/d/[SHEET_ID]/edit"
        }
        
        return {
            "status": "ready_for_export",
            "export_type": export_type,
            "preview_url": export_urls.get(export_type, ""),
            "instructions": "生成されたデータをGoogle Workspaceにインポートする手順",
            "data_format": "google_workspace_compatible"
        }

# サービスインスタンス
google_workspace_service = GoogleWorkspaceService()