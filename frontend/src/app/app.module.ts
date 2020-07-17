import { BrowserModule } from "@angular/platform-browser";
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { NgModule } from "@angular/core";
import { HttpClientModule } from "@angular/common/http";

import { NgxFilesizeModule } from "ngx-filesize";

import { AppRoutingModule, routingComponents } from "./app-routing.module";
import { AppComponent } from "./app.component";
import { HeaderComponent } from "./header/header.component";
import { FooterComponent } from "./footer/footer.component";
import { StateService } from "./state.service";
import { ColorPaletteComponent } from './color-palette/color-palette.component';
import { ImageFileInputComponent } from './image-file-input/image-file-input.component';
import { LoaderOverlayComponent } from './loader-overlay/loader-overlay.component';


@NgModule({
  declarations: [
    AppComponent,
    HeaderComponent,
    FooterComponent,
    routingComponents,
    ColorPaletteComponent,
    ImageFileInputComponent,
    LoaderOverlayComponent,
  ],
  imports: [
    BrowserModule,
    AppRoutingModule,
    FormsModule,
    ReactiveFormsModule,
    HttpClientModule,
    NgxFilesizeModule,
  ],
  providers: [StateService],
  bootstrap: [AppComponent]
})
export class AppModule { }
