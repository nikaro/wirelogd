package main

import (
	"os"

	"github.com/rs/zerolog/log"
	"github.com/spf13/cobra"
	"github.com/spf13/cobra/doc"
)

func init() {
	rootCmd.AddCommand(man)
	rootCmd.CompletionOptions.HiddenDefaultCmd = true
}

var man = &cobra.Command{
	Use:    "man",
	Short:  "Generate manpage",
	Hidden: true,
	Run: func(cmd *cobra.Command, args []string) {
		header := &doc.GenManHeader{}
		err := doc.GenMan(rootCmd, header, os.Stdout)
		if err != nil {
			log.Error().Err(err).Send()
			os.Exit(1)
		}
	},
}
