下面这些可以直接拿去生成音乐测试，偏 **MusicSpec 结构化描述**，覆盖风格、段落、乐器、节奏、混音、版本修改等场景。

## 一、基础风格生成测试

1. 生成一首雨夜电影感钢琴曲，C minor，72 BPM，4/4，结构为 intro、verse、chorus、outro；主旋律忧郁，钢琴为主，Pad 轻铺底，副歌音区略升高，结尾回到安静氛围。

2. 生成一首中国风影视配乐，D minor，80 BPM，4/4，包含 flute、erhu、string ensemble、low tom percussion；旋律使用东方五声音阶感觉，弦乐持续铺底，副歌更宏大。

3. 生成一首 Lo-fi hiphop，A minor，82 BPM，4/4，鼓组带轻微 swing，使用 electric piano、warm pad、electric bass、soft drums；整体温暖、松弛、适合夜晚学习。

4. 生成一首游戏 Boss 战音乐，E minor，140 BPM，4/4，包含 string ostinato、brass、distortion guitar、heavy drums、synth bass；节奏紧张，副歌或 climax 更强烈。

5. 生成一首冥想氛围音乐，F major，60 BPM，4/4，使用 warm pad、soft piano、choir aahs、低频环境音感；旋律极简，和声变化缓慢，整体平静。

6. 生成一首流行情歌伴奏，G major，76 BPM，4/4，结构为 intro、verse、pre_chorus、chorus、bridge、final_chorus、outro；钢琴和吉他为主，副歌旋律更有记忆点。

7. 生成一首电子律动音乐，C minor，124 BPM，4/4，使用 synth bass、lead sawtooth、pad、dance drums；kick 稳定，bass 有律动，副歌进入时能量提升。

8. 生成一首摇滚主题音乐，E minor，128 BPM，4/4，包含 distortion guitar、electric bass、rock drums、lead guitar；verse 节奏克制，chorus 强劲开阔。

## 二、MusicSpec 结构压力测试

9. 生成一首 90 秒 cinematic trailer 音乐，结构为 intro、build、climax、outro；从低强度逐渐增强到强烈高潮，包含 strings、brass、choir、taiko-like drums，最后突然收束。

10. 生成一首 7/8 拍的奇数拍实验电子音乐，B minor，110 BPM，包含 synth lead、synth bass、drums、pad；节奏要有循环感但不要太混乱。

11. 生成一首 3/4 拍的梦幻华尔兹，D major，96 BPM，包含 piano、strings、flute、soft percussion；旋律优雅，和声温暖，适合童话场景。

12. 生成一首只有 4 个轨道的极简音乐：piano、bass、drums、pad；A minor，90 BPM，4/4，要求每个轨道作用清晰，不要过度编曲。

13. 生成一首多段落完整流行歌曲伴奏，结构为 intro、verse1、chorus1、verse2、chorus2、bridge、final_chorus、outro；要求每段有明显差异，副歌能量高于主歌。

14. 生成一首没有鼓组的安静钢琴弦乐曲，C major，68 BPM，使用 piano、string ensemble、warm pad；强调旋律和和声，不要生成 drums track。

15. 生成一首以贝斯和鼓为核心的 funk groove，D minor，105 BPM，包含 electric bass finger、clean guitar、drums、brass hits；贝斯要和 kick 呼应。

16. 生成一首 suspense 悬疑配乐，F# minor，72 BPM，使用 low strings、dark pad、pizzicato strings、soft percussion；和声紧张但不要太吵。

## 三、测试旋律 / 和声 / 鼓组 / 贝斯增强

17. 生成一首旋律主题明确的钢琴曲，要求 intro 出现简短 motif，verse 做第一次陈述，chorus 做升高变奏，outro 回收主题。

18. 生成一首重点测试终止式的流行伴奏，C major，84 BPM；verse 结尾使用半终止感，chorus 结尾使用 V-I 的稳定终止，bridge 使用对比和声。

19. 生成一首重点测试鼓组 fill 的摇滚曲，E minor，132 BPM；每个段落进入 chorus 前都有明显 tom/snare fill，chorus 第一拍有 crash。

20. 生成一首重点测试贝斯 groove 的 lo-fi 曲，A minor，82 BPM；bass 需要跟随 kick，使用 root、fifth、octave 和少量 passing tone。

21. 生成一首重点测试 strings/pad voice leading 的电影配乐，D minor，76 BPM；弦乐和 Pad 需要平滑连接和弦，副歌增加厚度，outro 逐渐变薄。

22. 生成一首重点测试 SoundFont 选择的管弦风格作品，C minor，90 BPM，优先使用 orchestral / cinematic soundfont hint，但没有音源时也必须能 fallback 渲染。

## 四、自然语言修改测试

23. 在当前歌曲基础上，把副歌变得更宏大：提高弦乐和 Pad 厚度，鼓组更强，旋律音区升高，但不要改变主歌。

24. 在当前歌曲基础上，把整体改成 Lo-fi 版本：降低速度，加入 swing 鼓组，使用 electric piano 和 warm pad，减少弦乐和 brass。

25. 在当前歌曲基础上，只修改 bridge：让 bridge 更神秘，使用 minor 和声、低音 Pad 和稀疏鼓点，其他段落保持不变。

26. 在当前歌曲基础上，强化贝斯律动：让 bass 更贴近 kick，增加 root、fifth、octave 跳进，但不要盖过主旋律。

27. 在当前歌曲基础上，弱化鼓组并突出钢琴：降低 drums velocity，减少 fill，让 piano melody 更清晰。

28. 在当前歌曲基础上，恢复成更适合冥想的版本：降低 BPM，减少鼓组，使用长音 Pad，旋律更稀疏。

## 五、极端 / 回归测试

29. 生成一首 30 秒短音乐，只有 intro、chorus、outro 三段，要求结构完整但不要生成过多音符。

30. 生成一首 3 分钟长音乐，包含多个重复副歌和 bridge，要求版本、MIDI、WAV、Piano Roll、stems 导出都能正常处理。

31. 生成一首没有明确风格词的音乐：情绪是“孤独但有希望”，系统需要自动判断合适的 tempo、key、乐器和结构。

32. 生成一首包含中西混合元素的音乐：erhu、flute、strings、electric bass、soft drums 同时存在，但编曲不要混乱。

你可以先用 **1、3、7、17、19、23、29、31** 做一轮快速测试；它们能覆盖生成、风格识别、旋律主题、鼓组、修改、短结构和模糊 prompt。
