package provider

import (
	"context"
	"os"

	"github.com/hashicorp/terraform-plugin-framework/datasource"
	"github.com/hashicorp/terraform-plugin-framework/path"
	"github.com/hashicorp/terraform-plugin-framework/provider"
	"github.com/hashicorp/terraform-plugin-framework/provider/schema"
	"github.com/hashicorp/terraform-plugin-framework/resource"
	"github.com/hashicorp/terraform-plugin-framework/types"
	"github.com/remilapeyre/watson/internal/client"
)

// Ensure watsonProvider satisfies various provider interfaces.
var _ provider.Provider = &watsonProvider{}

// watsonProvider defines the provider implementation.
type watsonProvider struct {
	// version is set to the provider version on release, "dev" when the
	// provider is built and ran locally, and "test" when running acceptance
	// testing.
	version string
}

// watsonProviderModel describes the provider data model.
type watsonProviderModel struct {
	Address types.String `tfsdk:"address"`
	Scheme  types.String `tfsdk:"scheme"`
	Stack   types.String `tfsdk:"stack"`
}

func (p *watsonProvider) Metadata(ctx context.Context, req provider.MetadataRequest, resp *provider.MetadataResponse) {
	resp.TypeName = "watson"
	resp.Version = p.version
}

func (p *watsonProvider) Schema(ctx context.Context, req provider.SchemaRequest, resp *provider.SchemaResponse) {
	resp.Schema = schema.Schema{
		Attributes: map[string]schema.Attribute{
			"address": schema.StringAttribute{
				MarkdownDescription: "Example provider attribute",
				Optional:            true,
			},
			"scheme": schema.StringAttribute{
				MarkdownDescription: "",
				Optional:            true,
			},
			"stack": schema.StringAttribute{
				Optional: true,
			},
		},
	}
}

func (p *watsonProvider) Configure(ctx context.Context, req provider.ConfigureRequest, resp *provider.ConfigureResponse) {
	var config watsonProviderModel

	resp.Diagnostics.Append(req.Config.Get(ctx, &config)...)

	if resp.Diagnostics.HasError() {
		return
	}

	// Configuration values are now available.
	if config.Address.IsUnknown() {
		resp.Diagnostics.AddAttributeError(
			path.Root("address"),
			"Unknown watson API Host",
			"The provider cannot create the watson API client as there is an unknown configuration value for the watson API host. "+
				"Either target apply the source of the value first, set the value statically in the configuration, or use the watson_ADDRESS environment variable.",
		)
	}

	if config.Stack.IsUnknown() {
		resp.Diagnostics.AddAttributeError(
			path.Root("stack"),
			"Unknown watson API stack",
			"The provider cannot create the watson API client as there is an unknown configuration value for the watson API stack. "+
				"Either target apply the source of the value first, set the value statically in the configuration, or use the watson_STACK environment variable.",
		)
	}

	if config.Scheme.IsUnknown() {
		resp.Diagnostics.AddAttributeError(
			path.Root("scheme"),
			"Unknown watson API stack",
			"The provider cannot create the watson API client as there is an unknown configuration value for the watson API scheme. "+
				"Either target apply the source of the value first, set the value statically in the configuration, or use the watson_SCHEME environment variable.",
		)
	}

	if resp.Diagnostics.HasError() {
		return
	}

	// Default values to environment variables, but override
	// with Terraform configuration value if set.

	address := os.Getenv("watson_ADDRESS")
	stack := os.Getenv("watson_STACK")
	scheme := os.Getenv("watson_SCHEME")

	if !config.Address.IsNull() {
		address = config.Address.ValueString()
	}
	if !config.Stack.IsNull() {
		stack = config.Stack.ValueString()
	}
	if !config.Scheme.IsNull() {
		scheme = config.Scheme.ValueString()
	}

	// If any of the expected configurations are missing, return
	// errors with provider-specific guidance.

	if address == "" {
		resp.Diagnostics.AddAttributeError(
			path.Root("address"),
			"Missing watson API Address",
			"The provider cannot create the watson API client as there is a missing or empty value for the watson API address. "+
				"Set the address value in the configuration or use the watson_ADDRESS environment variable. "+
				"If either is already set, ensure the value is not empty.",
		)
	}
	if stack == "" {
		resp.Diagnostics.AddAttributeError(
			path.Root("stack"),
			"Missing watson API stack",
			"The provider cannot create the watson API client as there is a missing or empty value for the watson API stack. "+
				"Set the stack value in the configuration or use the watson_STACK environment variable. "+
				"If either is already set, ensure the value is not empty.",
		)
	}

	if resp.Diagnostics.HasError() {
		return
	}

	conf := client.DefaultConfig()
	if address != "" {
		conf.Address = address
	}
	if scheme != "" {
		conf.Scheme = scheme
	}
	if stack != "" {
		conf.Stack = stack
	}

	client, err := client.NewClient(conf)
	if err != nil {
		resp.Diagnostics.AddError("Failed to create watson API client", err.Error())
		return
	}

	resp.DataSourceData = client
	resp.ResourceData = client
}

func (p *watsonProvider) Resources(ctx context.Context) []func() resource.Resource {
	return []func() resource.Resource{}
}

func (p *watsonProvider) DataSources(ctx context.Context) []func() datasource.DataSource {
	return []func() datasource.DataSource{
		NewOutputsDataSource,
	}
}

func New(version string) func() provider.Provider {
	return func() provider.Provider {
		return &watsonProvider{
			version: version,
		}
	}
}
