package main

import (
	"fmt"
	"sync"
	"time"
)

func main() {
	var wg sync.WaitGroup
	wg.Add(2) // 2つのタスクを待つ

	// 数字を印刷
	go func() {
		for i := 1; i <= 5; i++ {
			time.Sleep(100 * time.Millisecond) // タスクの切り替えを模擬
			fmt.Printf("%d ", i)
		}
		wg.Done()
	}()

	// 英字を印刷
	go func() {
		for i := 'a'; i <= 'e'; i++ {
			time.Sleep(100 * time.Millisecond) // タスクの切り替えを模擬
			fmt.Printf("%c ", i)
		}
		wg.Done()
	}()

	wg.Wait() // 2つのgoroutineが完了するのを待つ
	fmt.Println("\n並行性デモ完了")
}
