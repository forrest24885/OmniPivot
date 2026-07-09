#!/usr/bin/env python3
"""
诊断脚本：验证山雨组合时的粒子颜色流程
"""
import sys
from app import (
    extract_imagery, fuse_motifs, grow_motifs_on_skeleton,
    IMAGERY_COLOR_MAP, generate_particles, 
    PARTICLE_PALETTE, PARTICLE_PALETTE_TEAL,
    BASE_MOTIF_GENERATORS, _render_pattern_image
)

def test_full_flow():
    """测试完整的山雨粒子颜色流程"""
    print("=" * 60)
    print("山雨粒子颜色完整流程诊断")
    print("=" * 60)
    
    # 测试诗句集合
    test_poems = [
        "山雨同时出现",
        "山和雨",
        "雨落山间",
        "山雨",
        "雨从山来"
    ]
    
    for poem in test_poems:
        print(f"\n📝 诗句: {poem}")
        
        # 1. 提取意象
        imagery = extract_imagery(poem)
        print(f"   ✓ 提取的意象: {imagery}")
        
        # 2. 检查是否同时包含山和雨
        has_mountain = "山" in imagery
        has_rain = "雨" in imagery
        print(f"   ✓ 包含山: {has_mountain}, 包含雨: {has_rain}")
        
        # 3. 确定调色板
        selected_palette = PARTICLE_PALETTE_TEAL if (has_mountain and has_rain) else PARTICLE_PALETTE
        palette_name = "🟢 青蓝色" if selected_palette == PARTICLE_PALETTE_TEAL else "🟡 金色"
        print(f"   ✓ 选择的调色板: {palette_name}")
        
        # 4. 验证调色板值
        print(f"   ✓ 调色板值: {selected_palette}")
        
        # 5. 生成示例粒子
        test_particles = generate_particles(
            [(320, 320, 480, 480)], 
            num=10, 
            palette=selected_palette
        )
        
        # 验证所有粒子颜色都来自选定的调色板
        all_match = all(p['color'] in selected_palette for p in test_particles)
        print(f"   ✓ 粒子颜色验证: {'✅ 通过' if all_match else '❌ 失败'}")
        
        if all_match:
            # 显示前3个粒子的颜色
            for i in range(min(3, len(test_particles))):
                print(f"      粒子{i+1}: {test_particles[i]['color']}")
    
    print("\n" + "=" * 60)
    print("诊断完成!")
    print("=" * 60)
    
    # 验证"雨"是否在 BASE_MOTIF_GENERATORS 中
    print(f"\n🔍 验证:")
    print(f"   '雨' 在 BASE_MOTIF_GENERATORS 中: {'✅' if '雨' in BASE_MOTIF_GENERATORS else '❌'}")
    print(f"   PARTICLE_PALETTE_TEAL 已定义: {'✅' if PARTICLE_PALETTE_TEAL else '❌'}")
    print(f"   PARTICLE_PALETTE_TEAL 值: {PARTICLE_PALETTE_TEAL}")

if __name__ == "__main__":
    try:
        test_full_flow()
    except Exception as e:
        print(f"❌ 错误: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
