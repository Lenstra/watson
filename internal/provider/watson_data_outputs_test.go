package provider

import (
	"regexp"
	"testing"

	"github.com/hashicorp/terraform-plugin-testing/helper/resource"
	"github.com/hashicorp/terraform-plugin-testing/terraform"
)

func TestAccOutputsDataSource(t *testing.T) {
	resource.Test(t, resource.TestCase{
		ProtoV6ProviderFactories: testAccProtoV6ProviderFactories,
		PreCheck:                 func() { testAccPreCheck(t) },
		CheckDestroy: func(s *terraform.State) error {
			// Now check that the dependency has been saved
			stack, err := testClient.GetStack("backend/load-balancers")
			if err != nil {
				t.Fatal(err)
			}
			if stack == nil {
				t.Fatal(`failed to read stack "backend/load-balancers"`)
			}
			if len(stack.UsedBy) != 1 {
				t.Fatal(stack.UsedBy)
			}
			if stack.UsedBy[0].Id != "frontend/dev" {
				t.Fatalf("wrong value for used_by: %s", stack.UsedBy[0].Id)
			}
			return nil
		},
		Steps: []resource.TestStep{
			{
				Config: providerConfig + `data "watson_outputs" "test" {
					stack = "hello"
				}`,
				ExpectError: regexp.MustCompile(`"hello" is not a valid stack name`),
			},
			{
				Config: providerConfig + `data "watson_outputs" "test" {
					stack = "hello/world"
				}`,
				ExpectError: regexp.MustCompile(`No stack named "hello/world" could be found`),
			},
			{
				Config: providerConfig + `data "watson_outputs" "test" {
					stack = "backend/load-balancers"
				}`,
				Check: resource.ComposeAggregateTestCheckFunc(
					resource.TestCheckResourceAttr("data.watson_outputs.test", "id", "backend/load-balancers"),
					resource.TestCheckResourceAttr("data.watson_outputs.test", "stack", "backend/load-balancers"),
					resource.TestCheckResourceAttr("data.watson_outputs.test", "outputs.%", "1"),
					resource.TestCheckResourceAttr("data.watson_outputs.test", "outputs.hostname.%", "4"),
					resource.TestCheckResourceAttr("data.watson_outputs.test", "outputs.hostname.value", "https://hello.eu-central-1.blabla"),
					resource.TestCheckResourceAttr("data.watson_outputs.test", "outputs.hostname.sensitive", "false"),
					resource.TestCheckResourceAttr("data.watson_outputs.test", "outputs.hostname.deprecated", ""),
					resource.TestCheckResourceAttr("data.watson_outputs.test", "outputs.hostname.warning", ""),
				),
			},
		},
	})
}
