Title: MySQL 性能调优检查清单
Date: 2018-02-12 00:00
Modified: 2018-02-12 00:00
Slug: verses/d535e2c4-eb74-4f7c-bdf4-2da92aa2a0bb
Category: verses
Authors: Ju Lin
verse_category: Database

[查看原文](http://www.jonathanlevin.co.uk/2018/02/my-mysql-linux-tuning-checklist.html)

MySQL 运行在 Linux 上，在调优性能时要关注的几块地方：

* IOscheduler,
* 内核版本
* IRQbalance
* 文件系统，开 noatime, nobarrier 选项
* 调 ulimit
* 调 swappiness 内核参数
* 上 Jemalloc，如果必要的话
* 配置 iptables, pam
