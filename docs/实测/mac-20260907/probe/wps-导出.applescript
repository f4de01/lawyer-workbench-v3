-- 依据 issue #41。WPS for Mac 的 AppleScript 支持没有公开文档，所以这里不假设任何动词可用：
-- 每一种写法单独 try，把标签与结果原样打出来。目的不是让它成功，是知道哪一种可用、不可用时报什么。
-- 参数：1 = app 名（如 "wpsoffice" 或 "WPS Office"），2 = 输入 docx 的 POSIX 路径，3 = 输出 PDF 的 POSIX 路径

on run argv
	set appName to item 1 of argv
	set inPOSIX to item 2 of argv
	set outPOSIX to item 3 of argv
	set inHFS to (POSIX file inPOSIX) as text
	set outHFS to (POSIX file outPOSIX) as text
	set report to {}

	-- 第 0 关：这个 app 认不认 AppleScript。不认的话后面全都免谈，直接返回。
	try
		tell application appName to activate
		set end of report to "activate: OK"
	on error e0
		set end of report to "activate: 失败 -> " & e0
		set end of report to "==> 这个 app 连 activate 都不认，AppleScript 这条路不通。"
		return my 连(report)
	end try

	delay 3

	-- 第 1 关：能不能开文档。两种路径写法、两种动词各试一次。
	set opened to false
	try
		tell application appName to open inHFS
		set end of report to "open(HFS): OK"
		set opened to true
	on error e1
		set end of report to "open(HFS): 失败 -> " & e1
	end try
	if not opened then
		try
			tell application appName to open inPOSIX
			set end of report to "open(POSIX): OK"
			set opened to true
		on error e2
			set end of report to "open(POSIX): 失败 -> " & e2
		end try
	end if
	if not opened then
		try
			tell application appName to open (POSIX file inPOSIX)
			set end of report to "open(POSIX file 对象): OK"
			set opened to true
		on error e3
			set end of report to "open(POSIX file 对象): 失败 -> " & e3
		end try
	end if

	-- 第 2 关：它把自己的文档叫什么。能问出来说明有对象模型。
	try
		tell application appName to set n to (count of documents)
		set end of report to "count of documents: " & (n as text)
	on error e4
		set end of report to "count of documents: 失败 -> " & e4 & "（没有 documents 对象模型）"
	end try

	try
		tell application appName to set nm to name of front document
		set end of report to "front document name: " & nm
	on error e5
		set end of report to "front document name: 失败 -> " & e5
	end try

	-- 第 3 关：分页强制。Word 那边是 compute statistics，WPS 有没有对等物是 #41 第 3 问。
	try
		tell application appName to set pg to (compute statistics front document statistic statistic pages)
		set end of report to "compute statistics(pages): OK -> " & (pg as text)
	on error e6
		set end of report to "compute statistics(pages): 失败 -> " & e6
	end try
	try
		tell application appName to repaginate front document
		set end of report to "repaginate: OK"
	on error e7
		set end of report to "repaginate: 失败 -> " & e7
	end try
	try
		tell application appName to set pc to (count of pages of front document)
		set end of report to "count of pages: " & (pc as text)
	on error e8
		set end of report to "count of pages: 失败 -> " & e8
	end try

	-- 第 4 关：导出 PDF。Word 系、通用系、Pages 系三种写法都试。
	try
		tell application appName to save front document in outHFS as "PDF"
		set end of report to "save ... in ... as PDF(HFS): OK"
	on error e9
		set end of report to "save ... in ... as PDF(HFS): 失败 -> " & e9
	end try
	try
		tell application appName to save as front document file name outHFS file format format PDF
		set end of report to "save as(Word 写法): OK"
	on error e10
		set end of report to "save as(Word 写法): 失败 -> " & e10
	end try
	try
		tell application appName to export front document to (POSIX file outPOSIX) as "PDF"
		set end of report to "export ... to ... as PDF: OK"
	on error e11
		set end of report to "export ... to ... as PDF: 失败 -> " & e11
	end try

	-- 第 5 关：退而求其次，能不能走打印管线出 PDF（打印件是最终形态，这条通了也有用）
	try
		tell application appName to print front document
		set end of report to "print front document: OK（会不会弹打印框要看回显）"
	on error e12
		set end of report to "print front document: 失败 -> " & e12
	end try

	try
		tell application appName to close front document saving no
		set end of report to "close: OK"
	on error e13
		set end of report to "close: 失败 -> " & e13
	end try

	return my 连(report)
end run

on 连(lst)
	set out to ""
	repeat with x in lst
		set out to out & (x as text) & linefeed
	end repeat
	return out
end 连
