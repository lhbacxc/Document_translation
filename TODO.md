


- 看是否可以生成的英文文档加上原来的图，即不用自己配图，现在生成的英文文档只有文字版


- 生成的文档格式的问题，比如说首行缩进，行间距等
- 将使用的所有skill所需的依赖，都写在项目概览中，以及修改skill中，它们可以创建一个pyhton虚拟环境从而避免虚拟环境冗余
- 如果input中有多个文件待转换的话（不指定哪个文件），要先将一个文件全部的流程走完（最后生成docx默认先不选） 
- 封装成 skill，但是还有着其他的 skill 需要参与，这个项目概览有点太复杂了，需要简化一下，因为 skill 是渐进式纰漏，可能会更好一些？

- （优先级低）文献引用问题，生成的docx文献并不具备 Zotero 的域代码，所以不能实时编辑，现在的方法是手动添加

- （优先级低）conda run 在 Windows 上遇到编码问题。改用 PowerShell 直接激活环境，直接执行 python 脚本。
    conda run -n PDF_AIGC python extract_text.py input/整体流程测试.docx
    这是 Windows 系统编码问题。conda run 遇到了中文路径的编码错误。让我换一种方式，直接激活环境后执行脚本。
    conda activate PDF_AIGC; python extract_text.py input/整体流程测试.docx
    这个是成功的，成功生成文件，虽然控制台输出的依旧是乱码


- ✅表格问题，最后生成的 docx 和 md 文档都无法正常的显示表格
