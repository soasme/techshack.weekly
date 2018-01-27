Title: 图数据库起步：ACID v/s BASE
Date: 2018-01-25 00:00
Modified: 2018-01-25 00:00
Slug: verses/3cfdefff-04a3-417f-81d7-d8a1b7a2deb7
Category: verses
Authors: Ju Lin
verse_category: System Design

[查看原文](https://neo4j.com/blog/acid-vs-base-consistency-models-explained/)

数据库有两种一致性模型，ACID 和 BASE。

* ACID：Atomic， Consistent，Isolated， Durable。这四个特性保证一个事务是完整的，其数据是一致的，持久地存储在硬盘上。
* BASE：Basic Availability，Soft-state，Eventual Consistency。BASE 比 ACID 更宽松，它优先考虑可用性，不保证写时 replicated 数据的一致性，但能保证最终一致性。

这两种数据库一致性模型适应的场景不太一样，如果用 BASE，那得在应用层面对数据一致性有一些处理。
