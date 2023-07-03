package provider

import (
	"fmt"
	"log"
	"os"
	"os/exec"
	"testing"
	"time"

	"github.com/Lenstra/watson/internal/client"
	"github.com/hashicorp/terraform-plugin-framework/providerserver"
	"github.com/hashicorp/terraform-plugin-go/tfprotov6"

	"github.com/phayes/freeport"
)

const (
	// providerConfig is a shared configuration to combine with the actual
	// test configuration so the watson client is properly configured.
	// It is also possible to use the watson_ environment variables instead,
	// such as updating the Makefile and running the testing through that tool.
	providerConfig = `
provider "watson" {}
`
)

var (
	testAccProtoV6ProviderFactories = map[string]func() (tfprotov6.ProviderServer, error){
		"watson": providerserver.NewProtocol6WithError(New("test")()),
	}
	testClient *client.Client = nil
)

func testAccPreCheck(t *testing.T) {
	port, err := freeport.GetFreePort()
	if err != nil {
		log.Fatal(err)
	}

	path, err := exec.LookPath("./../../manage.py")
	if err != nil {
		t.Fatal(err)
	}
	addrport := fmt.Sprintf("127.0.0.1:%d", port)
	cmd := exec.Command(
		path,
		"testserver",
		"sample.yaml",
		"--addr",
		addrport,
	)
	if os.Getenv("TF_LOG_SERVER") != "" {
		cmd.Stdout = os.Stdout
		cmd.Stderr = os.Stderr
	}
	if err := cmd.Start(); err != nil {
		t.Fatal(err)
	} else {
		t.Cleanup(func() {
			cmd.Process.Kill()
		})
	}

	time.Sleep(1 * time.Second)

	t.Setenv("watson_ADDRESS", addrport)
	t.Setenv("watson_SCHEME", "http")
	t.Setenv("watson_STACK", "frontend/dev")

	config := client.DefaultConfig()
	testClient, err = client.NewClient(config)
	if err != nil {
		t.Fatal(err)
	}
}
