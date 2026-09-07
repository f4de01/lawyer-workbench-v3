-- 依据 issue #41。对一件 docx 依次试几种写法，每种都单独 try，把标签与结果原样打出来。
-- 目的不是让它成功，是知道哪一种可用、不可用时报什么。
-- 参数：1 = 输入 docx 的 POSIX 路径，2 = 输出 PDF 的 POSIX 路径

on run argv
	set inPOSIX to item 1 of argv
	set outPOSIX to item 2 of argv
	set inHFS to (POSIX file inPOSIX) as text
	set outHFS to (POSIX file outPOSIX) as text
	set report to {}

	tell application "Microsoft Word"
		activate

		-- 打开：两种路径写法各试一次
		set theDoc to missing value
		try
			set theDoc to open file name inHFS
			set end of report to "打开(HFS路径): OK"
		on error e
			set end of report to "打开(HFS路径): 失败 -> " & e
		end try
		if theDoc is missing value then
			try
				set theDoc to open file name inPOSIX
				set end of report to "打开(POSIX路径): OK"
			on error e2
				set end of report to "打开(POSIX路径): 失败 -> " & e2
			end try
		end if
		if theDoc is missing value then
			return my 连(report)
		end if

		-- 分页强制：对应 Windows 侧的 ComputeStatistics(2)，ADR-0006 记的那个坑
		try
			set pg to compute statistics theDoc statistic statistic pages
			set end of report to "compute statistics(pages): OK -> " & (pg as text)
		on error e3
			set end of report to "compute statistics(pages): 失败 -> " & e3
		end try

		try
			repaginate theDoc
			set end of report to "repaginate: OK"
		on error e4
			set end of report to "repaginate: 失败 -> " & e4
		end try

		-- 导出：三种写法
		try
			save as theDoc file name outHFS file format format PDF
			set end of report to "save as(format PDF, HFS): OK"
		on error e5
			set end of report to "save as(format PDF, HFS): 失败 -> " & e5
			try
				save as theDoc file name outPOSIX file format format PDF
				set end of report to "save as(format PDF, POSIX): OK"
			on error e6
				set end of report to "save as(format PDF, POSIX): 失败 -> " & e6
			end try
		end try

		-- 页数（导出前后各问一次，看它认不认）
		try
			set pc to (count of pages of theDoc)
			set end of report to "count pages: " & (pc as text)
		on error e7
			set end of report to "count pages: 失败 -> " & e7
		end try

		try
			close theDoc saving no
			set end of report to "关闭: OK"
		on error e8
			set end of report to "关闭: 失败 -> " & e8
		end try
	end tell

	return my 连(report)
end run

on 连(lst)
	set out to ""
	repeat with x in lst
		set out to out & (x as text) & linefeed
	end repeat
	return out
end 连
