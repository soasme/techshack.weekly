Title: 2010-2015 Instagram 的 五年，如何应对突发流量和宕机
Date: 2018-02-08 00:00
Modified: 2018-02-08 00:00
Slug: verses/ddefc7d8-cd4f-44e6-a314-f7f6cc62df18
Category: verses
Authors: Ju Lin
verse_category: System Design

[查看原文](https://medium.com/backchannel/war-stories-3696d00207ff)

Instagram 上线第一天服务器资源仅相当于一台 Macbook Pro，但要 Serve  25000 个用户已经很吃力了。好在 IT 行业素来有分享实践的传统，偷师学艺，没几天就迁移到 AWS 上，用云服务买来了发展的时间。

Virginia 暴风肆虐导致 AWS us-east 机房断电，他们有一半的实例没电了。由于基本功没做，网站没法迅速搞起来，结果花了整整 36 个小时重建整个 infrastructure。经过这个事故，他们痛定思痛，去掉了脆弱的 bash 部署脚本，用上了成熟的 chef，另外采用 WAL-E 和 Postgres WAL shipping replication，并把整个后端运行在异地数据中心。

并入 F 家以后做了一次数据大迁移，相当于 100mph 高速运行的跑车逐个更换零件。他们搞了 8 人的小团队，开发了一系列工具能从 EC2 导数据回自家数据中心。好处是能用上 F 家的各种内部服务了，不用再去造轮子。  
