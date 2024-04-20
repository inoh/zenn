package main

import (
	"fmt"
	"sync"
)

func main() {
	var wg sync.WaitGroup
	wg.Add(2) // 2つのタスクを待つ

	// 数字を印刷
	go func() {
		for i := 1; i <= 5; i++ {
			fmt.Printf("%d ", i)
		}
		wg.Done()
	}()

	// 英字を印刷
	go func() {
		for i := 'a'; i <= 'e'; i++ {
			fmt.Printf("%c ", i)
		}
		wg.Done()
	}()

	wg.Wait() // 2つのgoroutineが完了するのを待つ
	fmt.Println("\n並列性デモ完了")
}
